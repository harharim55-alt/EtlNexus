"""Health check endpoints.

- GET /health       — unauthenticated, minimal liveness probe (load balancers, k8s).
- GET /health/detail — admin-only, full service diagnostics including scheduler liveness.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.config import settings
from app.database import engine, get_db_session

router = APIRouter(tags=["health"])

# ---------------------------------------------------------------------------
# Scheduler liveness tracking
# ---------------------------------------------------------------------------

_last_sync_completed_at: datetime | None = None


def report_sync_completed() -> None:
    """Record that a scheduled sync/poll cycle completed successfully.

    Called by the scheduler after each successful sync or poll run.  The
    health detail endpoint uses this timestamp to detect a stale scheduler.
    """
    global _last_sync_completed_at
    _last_sync_completed_at = datetime.now(UTC)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
async def health_check() -> JSONResponse:
    """Minimal public liveness probe — no auth, no service details.

    Returns 200 ``{"status": "ok"}`` when the process is alive.
    No database or external-service checks are performed here; those are
    reserved for the authenticated detail endpoint to avoid leaking
    infrastructure information to unauthenticated callers.
    """
    return JSONResponse(content={"status": "ok"}, status_code=200)


@router.get(
    "/health/detail",
    dependencies=[Depends(require_role("admin"))],
)
async def health_detail(
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Detailed health diagnostics — admin only.

    Checks:
    - Database connectivity (live SELECT 1)
    - Airflow client connection state
    - Spark Connect client connection state
    - DB connection pool statistics
    - Scheduler liveness (when ``settings.scheduler_enabled``)

    Returns HTTP 503 if the database is unreachable.
    """
    from app.integrations.airflow_client import airflow_client
    from app.integrations.spark_connect_client import spark_connect_client

    # Verify actual database connectivity
    db_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    # Connection pool status
    pool = engine.pool
    pool_status = {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }

    response_data: dict = {
        "status": "healthy" if db_ok else "unhealthy",
        "services": {
            "database": "connected" if db_ok else "disconnected",
            "airflow": "connected" if airflow_client.is_connected else "unknown",
            "spark_connect": "connected" if spark_connect_client.is_connected else "unknown",
        },
        "db_pool": pool_status,
    }

    # Scheduler liveness check
    if settings.scheduler_enabled:
        stale_threshold = timedelta(
            minutes=settings.airflow_poll_interval_minutes * 2
        )
        if _last_sync_completed_at is None:
            # Not yet completed — treat as unknown rather than stale on fresh start
            scheduler_status = "unknown"
        elif datetime.now(UTC) - _last_sync_completed_at > stale_threshold:
            scheduler_status = "stale"
        else:
            scheduler_status = "ok"
        response_data["scheduler"] = scheduler_status

    status_code = 200 if db_ok else 503
    return JSONResponse(content=response_data, status_code=status_code)
