from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
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

    airflow_ok = await airflow_client.check_health()

    return {
        "status": "healthy" if db_ok else "unhealthy",
        "services": {
            "database": "connected" if db_ok else "disconnected",
            "airflow": "connected" if airflow_ok else "disconnected",
            "iceberg": "connected" if iceberg_client.is_connected else "disconnected",
        },
    }
