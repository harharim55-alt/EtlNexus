"""Pure ASGI middleware classes for body size limiting, request ID injection, and request logging.

These classes implement the raw ASGI interface (scope/receive/send) so they can be
composed with any ASGI-compatible framework without depending on Starlette/FastAPI
middleware helpers.
"""

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from app.logging_config import request_id_var
from app.routers.metrics import record_request

logger = logging.getLogger(__name__)

# ASGI type aliases
Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


async def _send_json_response(send: Send, *, status: int, body: bytes) -> None:
    """Send a minimal JSON HTTP response directly via raw ASGI send callable.

    Args:
        send: The ASGI send callable from the middleware chain.
        status: HTTP status code to return.
        body: Pre-encoded response body bytes.
    """
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class BodySizeLimitMiddleware:
    """Reject HTTP requests whose Content-Length exceeds a configurable maximum.

    The check is performed on the ``content-length`` header only — streaming
    requests without a declared length pass through unchecked.  A 413 JSON
    response is returned directly via raw ASGI without invoking the downstream
    application.  Non-HTTP scopes (websocket, lifespan) are always forwarded
    unchanged.

    Args:
        app: The downstream ASGI application.
        max_size: Maximum allowed value for the Content-Length header in bytes.
            Defaults to 1 MiB (1 048 576 bytes).
    """

    def __init__(self, app: ASGIApp, max_size: int = 1_048_576) -> None:
        self.app = app
        self.max_size = max_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
        for name, value in headers:
            if name.lower() == b"content-length":
                try:
                    declared_length = int(value)
                except ValueError:
                    break
                if declared_length > self.max_size:
                    body = json.dumps({"detail": "Request body too large"}).encode()
                    await _send_json_response(send, status=413, body=body)
                    return
                break

        await self.app(scope, receive, send)


class RequestIdMiddleware:
    """Generate a UUID request ID, expose it via a context variable, and echo it as a response header.

    The generated ID is stored in :data:`app.logging_config.request_id_var` so
    that structured log formatters can include it in every log record emitted
    during the request lifecycle.  The same ID is appended to the response as
    the ``X-Request-ID`` header by wrapping the ASGI ``send`` callable.

    Args:
        app: The downstream ASGI application.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        rid = str(uuid.uuid4())
        request_id_var.set(rid)
        rid_bytes = rid.encode()

        async def send_with_request_id(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                headers.append((b"x-request-id", rid_bytes))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_request_id)


class RequestLoggingMiddleware:
    """Log each HTTP request with method, path, status code, and wall-clock duration.

    Health-check requests to ``/api/health`` are silently skipped to avoid
    polluting logs with liveness probe noise.  After the downstream application
    finishes, the request is also recorded in the in-process metrics counters
    via :func:`app.routers.metrics.record_request`.

    Args:
        app: The downstream ASGI application.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if path == "/api/health":
            await self.app(scope, receive, send)
            return

        method: str = scope.get("method", "")
        status_code: int = 0
        start = time.monotonic()

        async def send_capturing_status(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_capturing_status)

        duration = time.monotonic() - start
        logger.info(
            "%s %s %d %.0fms",
            method,
            path,
            status_code,
            duration * 1000,
        )

        record_request(method, path, status_code, duration)
