"""Background task: Discover pipelines + lineage from Airflow task metadata."""

import logging

from app.database import async_session_factory
from app.services.airflow_sync_service import AirflowSyncService

logger = logging.getLogger(__name__)


async def sync_pipelines_from_airflow() -> None:
    """Discover pipelines from Airflow and sync metadata + lineage."""
    logger.info("Starting Airflow pipeline sync")
    try:
        async with async_session_factory() as session:
            service = AirflowSyncService(session)
            count = await service.sync_pipelines_from_airflow()
            logger.info("Airflow pipeline sync completed: %d pipelines synced", count)
    except Exception:
        logger.exception("Airflow pipeline sync task failed")
