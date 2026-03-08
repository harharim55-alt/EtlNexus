from fastapi import APIRouter

from app.integrations.airflow_client import airflow_client
from app.integrations.git_client import git_client
from app.integrations.iceberg_client import iceberg_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    airflow_ok = await airflow_client.check_health()
    git_ok = git_client.has_repo()

    return {
        "status": "healthy",
        "services": {
            "database": "connected",
            "airflow": "connected" if airflow_ok else "disconnected",
            "iceberg": "connected" if iceberg_client.is_connected else "disconnected",
            "git": "connected" if git_ok else "disconnected",
        },
    }
