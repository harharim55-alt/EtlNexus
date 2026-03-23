"""Catalog sync service — discovers pipelines from Iceberg catalog via Spark."""

import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.iceberg_client import iceberg_client
from app.models.pipeline import Pipeline, PipelineField

logger = logging.getLogger(__name__)


class CatalogSyncService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def sync_from_catalog(self) -> int:
        """Discover tables from Iceberg catalog via Spark and upsert as pipelines.

        Uses spark.table("catalog.db.table").schema to read Iceberg schemas.
        Returns the number of pipelines synced.
        """
        schemas = iceberg_client.get_all_schemas()
        if not schemas:
            logger.info("No table schemas discovered from Iceberg catalog")
            return 0

        synced = 0
        for table_schema in schemas:
            task_id = table_schema.table_name  # PascalCase, e.g. "PortScanCollector"

            # Find existing pipeline by task_id (PascalCase match)
            stmt = (
                select(Pipeline)
                .options(selectinload(Pipeline.fields))
                .where(Pipeline.task_id == task_id)
            )
            result = await self.session.execute(stmt)
            pipeline = result.scalar_one_or_none()

            if not pipeline:
                logger.debug(
                    "No pipeline with task_id=%s — skipping Iceberg schema",
                    task_id,
                )
                continue

            if table_schema.fields:
                await self._sync_fields(pipeline, table_schema.fields)

            synced += 1

        await self.session.commit()
        logger.info("Synced %d pipelines from Iceberg catalog", synced)
        return synced

    async def _sync_fields(self, pipeline, fields: list[dict]) -> None:
        """Sync schema fields from Spark StructType for a pipeline."""
        # Delete existing fields
        await self.session.execute(
            delete(PipelineField).where(PipelineField.pipeline_id == pipeline.id)
        )
        await self.session.flush()

        for i, field_info in enumerate(fields):
            pf = PipelineField(
                pipeline_id=pipeline.id,
                name=field_info["name"],
                data_type=field_info["type"],
                ordinal_position=i,
            )
            self.session.add(pf)

    @staticmethod
    def _table_to_display_name(table_name: str) -> str:
        """Convert table name to display name.

        E.g., "shopify_sales_sync" -> "Shopify Sales Sync"
        """
        return table_name.replace("_", " ").title()
