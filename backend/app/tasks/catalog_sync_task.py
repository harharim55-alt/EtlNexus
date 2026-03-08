"""Background task: Sync pipelines from Iceberg catalog via Spark."""

import logging

from app.database import async_session_factory
from app.services.catalog_sync_service import CatalogSyncService

logger = logging.getLogger(__name__)


async def sync_from_catalog() -> None:
    """Discover and sync pipelines from Iceberg catalog.

    Uses PySpark to read table schemas via spark.table().schema.
    Gracefully handles unavailable catalog.
    """
    logger.info("Starting scheduled Iceberg catalog sync")
    try:
        async with async_session_factory() as session:
            service = CatalogSyncService(session)
            count = await service.sync_from_catalog()
            logger.info("Catalog sync completed: %d pipelines synced", count)
    except Exception:
        logger.exception("Catalog sync task failed")
