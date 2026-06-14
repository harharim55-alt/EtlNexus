"""Background task: refresh the Postgres catalog mirror from Spark Connect.

Runs every ``CATALOG_MIRROR_INTERVAL_SECONDS``. In one session:
  1. CatalogMirrorService — read all Iceberg schemas from Spark Connect and
     replace the ``catalog_columns`` mirror table (the only live Spark call).
  2. CatalogSyncService — project the mirror onto data-product fields (pure
     in-DB), matched by ``Pipeline.task_id == table_name``.

End-user requests then read schema data from Postgres and never hit Spark.
"""

import logging

from app.database import async_session_factory
from app.services.catalog_mirror_service import CatalogMirrorService
from app.services.catalog_sync_service import CatalogSyncService

logger = logging.getLogger(__name__)


async def refresh_catalog_mirror() -> None:
    """Refresh the catalog mirror from Spark Connect, then project to product fields.

    Gracefully handles an unavailable Spark Connect server: a transient outage
    leaves the existing mirror (and therefore the product fields) intact.
    """
    logger.info("Starting Spark Connect catalog mirror refresh")
    try:
        async with async_session_factory() as session:
            schemas = await CatalogMirrorService(session).refresh_from_spark()
            projected = await CatalogSyncService(session).sync_from_catalog()
            logger.info(
                "Catalog mirror refresh complete: %d tables, %d projected",
                len(schemas),
                projected,
            )
    except Exception:
        logger.exception("Catalog mirror refresh failed")
