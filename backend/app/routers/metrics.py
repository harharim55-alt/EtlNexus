"""Lightweight Prometheus-format metrics endpoint.

Tracks request counts and duration — no external dependencies needed.
Counters are monotonically increasing (never cleared) for correct Prometheus rate calculations.
New metric keys are rejected when the cardinality cap is reached.
"""

import logging
import re
from collections import defaultdict

from fastapi import APIRouter, Depends, Response

from app.auth import require_role

logger = logging.getLogger(__name__)
router = APIRouter(tags=["metrics"])

# In-memory counters — monotonically increasing, never cleared
_request_counts: dict[str, int] = defaultdict(int)
_request_duration_sum: dict[str, float] = defaultdict(float)
_request_duration_count: dict[str, int] = defaultdict(int)

_MAX_METRIC_KEYS = 10_000
_cardinality_warned = False
_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)


def record_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    """Record a completed request for metrics."""
    global _cardinality_warned

    # Normalize path to avoid cardinality explosion (strip UUIDs and IDs)
    normalized = _normalize_path(path)
    key = f'{method}|{normalized}|{status_code}'
    dur_key = f'{method}|{normalized}'

    # If key already exists, always update (no cardinality impact)
    if key in _request_counts or dur_key in _request_duration_sum:
        _request_counts[key] += 1
        _request_duration_sum[dur_key] += duration_seconds
        _request_duration_count[dur_key] += 1
        return

    # Reject new keys when cardinality cap is reached
    if len(_request_counts) >= _MAX_METRIC_KEYS:
        if not _cardinality_warned:
            logger.warning("Metrics cardinality cap reached (%d keys) — new keys will be dropped", _MAX_METRIC_KEYS)
            _cardinality_warned = True
        return

    _request_counts[key] += 1
    _request_duration_sum[dur_key] += duration_seconds
    _request_duration_count[dur_key] += 1


def _normalize_path(path: str) -> str:
    """Replace UUID segments and numeric IDs with placeholders."""
    parts = path.strip("/").split("/")
    normalized = []
    for part in parts:
        # UUID pattern (8-4-4-4-12 hex)
        if _UUID_RE.match(part) or part.isdigit():
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized)


@router.get("/api/metrics", include_in_schema=False, dependencies=[Depends(require_role("admin"))])
async def prometheus_metrics() -> Response:
    """Return metrics in Prometheus exposition format."""
    from app.database import engine

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

    # Database connection pool gauges
    pool = engine.pool
    lines.append("# HELP db_pool_size Configured connection pool size")
    lines.append("# TYPE db_pool_size gauge")
    lines.append(f"db_pool_size {pool.size()}")
    lines.append("# HELP db_pool_checked_out Connections currently in use")
    lines.append("# TYPE db_pool_checked_out gauge")
    lines.append(f"db_pool_checked_out {pool.checkedout()}")
    lines.append("# HELP db_pool_checked_in Idle connections in pool")
    lines.append("# TYPE db_pool_checked_in gauge")
    lines.append(f"db_pool_checked_in {pool.checkedin()}")
    lines.append("# HELP db_pool_overflow Connections beyond pool size")
    lines.append("# TYPE db_pool_overflow gauge")
    lines.append(f"db_pool_overflow {pool.overflow()}")

    lines.append("")
    return Response(content="\n".join(lines), media_type="text/plain; charset=utf-8")
