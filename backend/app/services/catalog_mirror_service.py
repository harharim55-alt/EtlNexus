"""Catalog mirror service — refreshes the Postgres copy of the Iceberg catalog.

This is the ONLY component that reads Spark Connect live. A scheduled job calls
``refresh_from_spark()`` every ``CATALOG_MIRROR_INTERVAL_SECONDS``; everything
else (pipeline field projection, end-user reads) works off the mirrored rows in
Postgres.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.spark_connect_client import spark_connect_client
from app.repositories.catalog_mirror_repo import CatalogMirrorRepository

logger = logging.getLogger(__name__)


class CatalogMirrorService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CatalogMirrorRepository(session)

    async def refresh_from_spark(self) -> int:
        """Read all table schemas from Spark Connect and replace the mirror table.

        Returns the number of columns mirrored. If Spark Connect returns nothing
        (server down / no tables), the existing mirror is left untouched so a
        transient Spark outage never wipes the cached catalog.
        """
        try:
            schemas = await asyncio.wait_for(
                asyncio.to_thread(spark_connect_client.get_all_schemas),
                timeout=settings.catalog_mirror_spark_timeout_seconds,
            )
        except TimeoutError:
            # Don't hold the refresh lock waiting on a hung Spark server — abandon
            # this cycle so the next tick can retry. Mirror is left unchanged.
            logger.warning(
                "Spark Connect catalog read exceeded %ds — skipping this refresh",
                settings.catalog_mirror_spark_timeout_seconds,
            )
            return 0
        if not schemas:
            logger.info("No schemas from Spark Connect — leaving catalog mirror unchanged")
            return 0

        rows: list[dict] = []
        for table_schema in schemas:
            for ordinal, field_info in enumerate(table_schema.fields):
                rows.append({
                    "namespace": table_schema.namespace,
                    "table_name": table_schema.table_name,
                    "column_name": field_info["name"],
                    "data_type": field_info.get("type"),
                    "ordinal_position": ordinal,
                })

        count = await self.repo.replace_all(rows)
        await self.session.commit()
        logger.info(
            "Catalog mirror refreshed: %d columns across %d tables", count, len(schemas)
        )
        return count
