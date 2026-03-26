"""Lightweight Prometheus-format metrics endpoint.

Tracks request counts and duration — no external dependencies needed.
"""

import time
from collections import defaultdict

from fastapi import APIRouter, Response

router = APIRouter(tags=["metrics"])

# In-memory counters
_request_counts: dict[str, int] = defaultdict(int)
_request_duration_sum: dict[str, float] = defaultdict(float)
_request_duration_count: dict[str, int] = defaultdict(int)


def record_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    """Record a completed request for metrics."""
    # Normalize path to avoid cardinality explosion (strip UUIDs and IDs)
    normalized = _normalize_path(path)
    key = f'{method}|{normalized}|{status_code}'
    _request_counts[key] += 1
    dur_key = f'{method}|{normalized}'
    _request_duration_sum[dur_key] += duration_seconds
    _request_duration_count[dur_key] += 1


def _normalize_path(path: str) -> str:
    """Replace UUID segments and numeric IDs with placeholders."""
    parts = path.strip("/").split("/")
    normalized = []
    for part in parts:
        # UUID pattern (8-4-4-4-12 hex)
        if len(part) == 36 and part.count("-") == 4:
            normalized.append("{id}")
        elif part.isdigit():
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized)


@router.get("/api/metrics", include_in_schema=False)
async def prometheus_metrics() -> Response:
    """Return metrics in Prometheus exposition format."""
    lines: list[str] = []

    lines.append("# HELP http_requests_total Total HTTP requests")
    lines.append("# TYPE http_requests_total counter")
    for key, count in sorted(_request_counts.items()):
        method, path, status = key.split("|")
        lines.append(
            f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
        )

    lines.append("# HELP http_request_duration_seconds_sum Sum of HTTP request durations")
    lines.append("# TYPE http_request_duration_seconds_sum counter")
    for key, total in sorted(_request_duration_sum.items()):
        method, path = key.split("|")
        lines.append(
            f'http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {total:.6f}'
        )

    lines.append("# HELP http_request_duration_seconds_count Count of HTTP requests for duration")
    lines.append("# TYPE http_request_duration_seconds_count counter")
    for key, count in sorted(_request_duration_count.items()):
        method, path = key.split("|")
        lines.append(
            f'http_request_duration_seconds_count{{method="{method}",path="{path}"}} {count}'
        )

    lines.append("")
    return Response(content="\n".join(lines), media_type="text/plain; charset=utf-8")
