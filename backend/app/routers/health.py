from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, get_db_session
from app.integrations.airflow_client import airflow_client
from app.integrations.iceberg_client import iceberg_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_db_session)):
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

    response_data = {
        "status": "healthy" if db_ok else "unhealthy",
        "services": {
            "database": "connected" if db_ok else "disconnected",
            "airflow": "connected" if airflow_client.is_connected else "unknown",
            "iceberg": "connected" if iceberg_client.is_connected else "unknown",
        },
        "db_pool": pool_status,
    }
    status_code = 200 if db_ok else 503
    return JSONResponse(content=response_data, status_code=status_code)
