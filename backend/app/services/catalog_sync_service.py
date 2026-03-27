"""Catalog sync service — discovers pipelines from Iceberg catalog via PyIceberg."""

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
        """Discover tables from Iceberg catalog via PyIceberg and upsert as pipelines.

        Uses PyIceberg REST catalog to read table schemas.
        Returns the number of pipelines synced.
        """
        schemas = iceberg_client.get_all_schemas()
        if not schemas:
            logger.info("No table schemas discovered from Iceberg catalog")
            return 0

        # Bulk load all matching pipelines to avoid N+1 per-table SELECTs
        task_ids = [ts.table_name for ts in schemas]
        stmt = (
            select(Pipeline)
            .options(selectinload(Pipeline.fields))
            .where(Pipeline.task_id.in_(task_ids))
        )
        result = await self.session.execute(stmt)
        pipeline_by_task_id = {p.task_id: p for p in result.scalars().all()}

        synced = 0
        # Collect all pipeline IDs that have fields to sync for batch DELETE
        pipelines_to_sync: list[tuple] = []  # (pipeline, fields)
        for table_schema in schemas:
            task_id = table_schema.table_name
            pipeline = pipeline_by_task_id.get(task_id)
            if not pipeline:
                logger.debug(
                    "No pipeline with task_id=%s — skipping Iceberg schema",
                    task_id,
                )
                continue
            if table_schema.fields:
                pipelines_to_sync.append((pipeline, table_schema.fields))

        if pipelines_to_sync:
            # Batch DELETE all existing fields for matched pipelines
            pipeline_ids = [p.id for p, _ in pipelines_to_sync]
            await self.session.execute(
                delete(PipelineField).where(PipelineField.pipeline_id.in_(pipeline_ids))
            )
            await self.session.flush()

            # Batch INSERT all new fields
            new_fields: list[PipelineField] = []
            for pipeline, fields in pipelines_to_sync:
                for i, field_info in enumerate(fields):
                    new_fields.append(PipelineField(
                        pipeline_id=pipeline.id,
                        name=field_info["name"],
                        data_type=field_info["type"],
                        ordinal_position=i,
                    ))
            self.session.add_all(new_fields)
            synced = len(pipelines_to_sync)

        await self.session.commit()
        logger.info("Synced %d pipelines from Iceberg catalog", synced)
        return synced

    @staticmethod
    def _table_to_display_name(table_name: str) -> str:
        """Convert table name to display name.

        E.g., "shopify_sales_sync" -> "Shopify Sales Sync"
        """
        return table_name.replace("_", " ").title()
