"""Tests for the pure ASGI middleware classes in app.middleware.

Each middleware is tested in isolation using a minimal ASGI application that
immediately returns a 200 OK response.  The test harness drives the ASGI
lifecycle manually so there is no dependency on Starlette, FastAPI, or any
HTTP client library.
"""

import json
from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.middleware import (
    BodySizeLimitMiddleware,
    RequestIdMiddleware,
    RequestLoggingMiddleware,
)

# ---------------------------------------------------------------------------
# Shared ASGI helpers
# ---------------------------------------------------------------------------

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


def _make_http_scope(
    *,
    path: str = "/api/test",
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Scope:
    """Return a minimal ASGI HTTP connection scope."""
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers or [],
    }


def _make_websocket_scope(path: str = "/ws") -> Scope:
    """Return a minimal ASGI WebSocket connection scope."""
    return {
        "type": "websocket",
        "path": path,
        "headers": [],
    }


async def _noop_receive() -> dict[str, Any]:
    """Minimal receive callable that returns an empty HTTP request body."""
    return {"type": "http.request", "body": b"", "more_body": False}


class _ResponseCollector:
    """Collect ASGI send messages into a structured result for assertion."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def __call__(self, message: dict[str, Any]) -> None:
        self.messages.append(message)

    @property
    def status(self) -> int:
        for msg in self.messages:
            if msg["type"] == "http.response.start":
                return msg["status"]
        raise AssertionError("No http.response.start message found")

    def header(self, name: bytes) -> bytes | None:
        """Return the first response header value matching *name* (case-insensitive)."""
        for msg in self.messages:
            if msg["type"] == "http.response.start":
                for key, value in msg.get("headers", []):
                    if key.lower() == name.lower():
                        return value
        return None

    @property
    def body(self) -> bytes:
        for msg in self.messages:
            if msg["type"] == "http.response.body":
                return msg.get("body", b"")
        return b""


async def _simple_200_app(scope: Scope, receive: Receive, send: Send) -> None:
    """Minimal ASGI app that always returns 200 OK with an empty body."""
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b""})


# ---------------------------------------------------------------------------
# BodySizeLimitMiddleware
# ---------------------------------------------------------------------------


class TestBodySizeLimitMiddleware:
    """Tests for BodySizeLimitMiddleware."""

    @pytest.mark.asyncio
    async def test_allows_request_within_limit(self) -> None:
        """A Content-Length below the limit must pass through to the downstream app."""
        middleware = BodySizeLimitMiddleware(_simple_200_app, max_size=1_000)
        scope = _make_http_scope(headers=[(b"content-length", b"500")])
        collector = _ResponseCollector()

        await middleware(scope, _noop_receive, collector)

        assert collector.status == 200

    @pytest.mark.asyncio
    async def test_allows_request_exactly_at_limit(self) -> None:
        """A Content-Length equal to max_size is within the limit and must pass through."""
        middleware = BodySizeLimitMiddleware(_simple_200_app, max_size=1_000)
        scope = _make_http_scope(headers=[(b"content-length", b"1000")])
        collector = _ResponseCollector()

        await middleware(scope, _noop_receive, collector)

        assert collector.status == 200

    @pytest.mark.asyncio
    async def test_rejects_request_exceeding_limit(self) -> None:
        """A Content-Length above the limit must produce a 413 response."""
        middleware = BodySizeLimitMiddleware(_simple_200_app, max_size=1_000)
        scope = _make_http_scope(headers=[(b"content-length", b"1001")])
        collector = _ResponseCollector()

        await middleware(scope, _noop_receive, collector)

        assert collector.status == 413

    @pytest.mark.asyncio
    async def test_413_body_is_json_detail(self) -> None:
        """The 413 response body must be a JSON object with a 'detail' key."""
        middleware = BodySizeLimitMiddleware(_simple_200_app, max_size=100)
        scope = _make_http_scope(headers=[(b"content-length", b"9999")])
        collector = _ResponseCollector()

        await middleware(scope, _noop_receive, collector)

        payload = json.loads(collector.body)
        assert "detail" in payload

    @pytest.mark.asyncio
    async def test_allows_request_without_content_length(self) -> None:
        """Requests without a Content-Length header must always pass through."""
        middleware = BodySizeLimitMiddleware(_simple_200_app, max_size=1)
        scope = _make_http_scope(headers=[])
        collector = _ResponseCollector()

        await middleware(scope, _noop_receive, collector)

        assert collector.status == 200

    @pytest.mark.asyncio
    async def test_non_http_scope_passes_through(self) -> None:
        """Non-HTTP scopes (e.g. websocket) must be forwarded unchanged."""
        # Track whether the downstream app was called with the websocket scope
        received_scopes: list[Scope] = []

        async def capturing_app(scope: Scope, receive: Receive, send: Send) -> None:
            received_scopes.append(scope)

        middleware = BodySizeLimitMiddleware(capturing_app, max_size=1)
        scope = _make_websocket_scope()

        await middleware(scope, _noop_receive, lambda _: None)  # type: ignore[arg-type]

        assert len(received_scopes) == 1
        assert received_scopes[0]["type"] == "websocket"

    @pytest.mark.asyncio
    async def test_default_max_size_is_one_mib(self) -> None:
        """The default max_size must be 1 048 576 bytes (1 MiB)."""
        middleware = BodySizeLimitMiddleware(_simple_200_app)
        assert middleware.max_size == 1_048_576

    @pytest.mark.asyncio
    async def test_invalid_content_length_header_passes_through(self) -> None:
        """A malformed (non-numeric) Content-Length header must not cause a 413."""
        middleware = BodySizeLimitMiddleware(_simple_200_app, max_size=100)
        scope = _make_http_scope(headers=[(b"content-length", b"not-a-number")])
        collector = _ResponseCollector()

        await middleware(scope, _noop_receive, collector)

        assert collector.status == 200


# ---------------------------------------------------------------------------
# RequestIdMiddleware
# ---------------------------------------------------------------------------


class TestRequestIdMiddleware:
    """Tests for RequestIdMiddleware."""

    @pytest.mark.asyncio
    async def test_response_contains_x_request_id_header(self) -> None:
        """Every HTTP response must have an x-request-id header."""
        middleware = RequestIdMiddleware(_simple_200_app)
        scope = _make_http_scope()
        collector = _ResponseCollector()

        await middleware(scope, _noop_receive, collector)

        assert collector.header(b"x-request-id") is not None

    @pytest.mark.asyncio
    async def test_x_request_id_is_valid_uuid(self) -> None:
        """The x-request-id header value must be a valid UUID string."""
        import uuid as _uuid

        middleware = RequestIdMiddleware(_simple_200_app)
        scope = _make_http_scope()
        collector = _ResponseCollector()

        await middleware(scope, _noop_receive, collector)

        rid_bytes = collector.header(b"x-request-id")
        assert rid_bytes is not None
        # Must not raise
        parsed = _uuid.UUID(rid_bytes.decode())
        assert parsed.version == 4

    @pytest.mark.asyncio
    async def test_request_id_var_is_set_during_request(self) -> None:
        """The request_id_var context variable must be populated while the app runs."""
        from app.logging_config import request_id_var

        captured: list[str] = []

        async def capturing_app(scope: Scope, receive: Receive, send: Send) -> None:
            captured.append(request_id_var.get("-"))
            await _simple_200_app(scope, receive, send)

        middleware = RequestIdMiddleware(capturing_app)
        scope = _make_http_scope()
        collector = _ResponseCollector()

        await middleware(scope, _noop_receive, collector)

        assert len(captured) == 1
        assert captured[0] != "-"

    @pytest.mark.asyncio
    async def test_request_id_matches_header(self) -> None:
        """The context variable value must equal the x-request-id response header."""
        from app.logging_config import request_id_var

        captured: list[str] = []

        async def capturing_app(scope: Scope, receive: Receive, send: Send) -> None:
            captured.append(request_id_var.get("-"))
            await _simple_200_app(scope, receive, send)

        middleware = RequestIdMiddleware(capturing_app)
        scope = _make_http_scope()
        collector = _ResponseCollector()

        await middleware(scope, _noop_receive, collector)

        rid_in_header = collector.header(b"x-request-id")
        assert rid_in_header is not None
        assert rid_in_header.decode() == captured[0]

    @pytest.mark.asyncio
    async def test_each_request_gets_unique_id(self) -> None:
        """Consecutive requests must receive different request IDs."""
        middleware = RequestIdMiddleware(_simple_200_app)
        ids: list[bytes] = []

        for _ in range(3):
            scope = _make_http_scope()
            collector = _ResponseCollector()
            await middleware(scope, _noop_receive, collector)
            rid = collector.header(b"x-request-id")
            assert rid is not None
            ids.append(rid)

        assert len(set(ids)) == 3

    @pytest.mark.asyncio
    async def test_non_http_scope_passes_through_without_header(self) -> None:
        """Non-HTTP scopes must be forwarded without modification."""
        received_scopes: list[Scope] = []

        async def capturing_app(scope: Scope, receive: Receive, send: Send) -> None:
            received_scopes.append(scope)

        middleware = RequestIdMiddleware(capturing_app)
        scope = _make_websocket_scope()

        await middleware(scope, _noop_receive, lambda _: None)  # type: ignore[arg-type]

        assert len(received_scopes) == 1
        assert received_scopes[0]["type"] == "websocket"


# ---------------------------------------------------------------------------
# RequestLoggingMiddleware
# ---------------------------------------------------------------------------


class TestRequestLoggingMiddleware:
    """Tests for RequestLoggingMiddleware."""

    @pytest.mark.asyncio
    async def test_health_path_is_not_logged(self) -> None:
        """Requests to /api/health must not produce any log output."""
        with patch("app.middleware.logger") as mock_logger:
            middleware = RequestLoggingMiddleware(_simple_200_app)
            scope = _make_http_scope(path="/api/health")
            collector = _ResponseCollector()

            await middleware(scope, _noop_receive, collector)

            mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_health_path_response_passes_through(self) -> None:
        """The /api/health response must still be returned to the client."""
        middleware = RequestLoggingMiddleware(_simple_200_app)
        scope = _make_http_scope(path="/api/health")
        collector = _ResponseCollector()

        await middleware(scope, _noop_receive, collector)

        assert collector.status == 200

    @pytest.mark.asyncio
    async def test_non_health_path_is_logged(self) -> None:
        """Requests to any path other than /api/health must produce a log entry."""
        with (
            patch("app.middleware.logger") as mock_logger,
            patch("app.routers.metrics.record_request"),
        ):
            middleware = RequestLoggingMiddleware(_simple_200_app)
            scope = _make_http_scope(path="/api/pipelines", method="GET")
            collector = _ResponseCollector()

            await middleware(scope, _noop_receive, collector)

            mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_message_includes_method_path_status(self) -> None:
        """The log message must include the HTTP method, path, and status code."""
        with (
            patch("app.middleware.logger") as mock_logger,
            patch("app.routers.metrics.record_request"),
        ):
            middleware = RequestLoggingMiddleware(_simple_200_app)
            scope = _make_http_scope(path="/api/pipelines", method="GET")
            collector = _ResponseCollector()

            await middleware(scope, _noop_receive, collector)

            args = mock_logger.info.call_args
            # Format string is "%s %s %d %.0fms" with positional args
            positional = args[0]
            assert positional[1] == "GET"
            assert positional[2] == "/api/pipelines"
            assert positional[3] == 200

    @pytest.mark.asyncio
    async def test_record_request_is_called(self) -> None:
        """record_request must be called once per non-health request."""
        with (
            patch("app.middleware.logger"),
            patch("app.middleware.record_request") as mock_record,
        ):
            middleware = RequestLoggingMiddleware(_simple_200_app)
            scope = _make_http_scope(path="/api/pipelines", method="POST")
            collector = _ResponseCollector()

            await middleware(scope, _noop_receive, collector)

            mock_record.assert_called_once()
            call_args = mock_record.call_args[0]
            assert call_args[0] == "POST"
            assert call_args[1] == "/api/pipelines"
            assert call_args[2] == 200
            # Fourth arg is duration in seconds — must be a non-negative float
            assert isinstance(call_args[3], float)
            assert call_args[3] >= 0.0

    @pytest.mark.asyncio
    async def test_record_request_not_called_for_health(self) -> None:
        """record_request must not be called for /api/health requests."""
        with (
            patch("app.middleware.logger"),
            patch("app.middleware.record_request") as mock_record,
        ):
            middleware = RequestLoggingMiddleware(_simple_200_app)
            scope = _make_http_scope(path="/api/health")
            collector = _ResponseCollector()

            await middleware(scope, _noop_receive, collector)

            mock_record.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_http_scope_passes_through(self) -> None:
        """Non-HTTP scopes must be forwarded unchanged without logging."""
        received_scopes: list[Scope] = []

        async def capturing_app(scope: Scope, receive: Receive, send: Send) -> None:
            received_scopes.append(scope)

        with patch("app.middleware.logger") as mock_logger:
            middleware = RequestLoggingMiddleware(capturing_app)
            scope = _make_websocket_scope()

            await middleware(scope, _noop_receive, lambda _: None)  # type: ignore[arg-type]

            assert len(received_scopes) == 1
            mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_status_code_captured_from_downstream(self) -> None:
        """The status code logged must reflect the actual downstream response status."""

        async def not_found_app(scope: Scope, receive: Receive, send: Send) -> None:
            await send({"type": "http.response.start", "status": 404, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        with (
            patch("app.middleware.logger") as mock_logger,
            patch("app.routers.metrics.record_request"),
        ):
            middleware = RequestLoggingMiddleware(not_found_app)
            scope = _make_http_scope(path="/api/missing")
            collector = _ResponseCollector()

            await middleware(scope, _noop_receive, collector)

            args = mock_logger.info.call_args[0]
            assert args[3] == 404
