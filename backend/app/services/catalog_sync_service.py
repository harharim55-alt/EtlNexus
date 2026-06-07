"""Catalog sync service — projects the Postgres catalog mirror onto pipeline fields.

Reads the mirrored Iceberg schemas from the ``catalog_columns`` table (populated
by ``CatalogMirrorService`` from Spark Connect) and materializes them as
``PipelineField`` rows, matching mirror ``table_name`` to ``Pipeline.task_id``.
This step is pure in-DB — it never touches Spark Connect.
"""

import logging
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline import Pipeline, PipelineField
from app.repositories.catalog_mirror_repo import CatalogMirrorRepository

logger = logging.getLogger(__name__)


class CatalogSyncService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def sync_from_catalog(self) -> int:
        """Project the catalog mirror onto pipeline fields.

        Reads schemas from the Postgres mirror (not Spark) and upserts them onto
        matching pipelines. Returns the number of pipelines synced.
        """
        mirror_rows = await CatalogMirrorRepository(self.session).list_all()
        if not mirror_rows:
            logger.info("Catalog mirror empty — nothing to project to pipeline fields")
            return 0

        # Group mirror columns by table (rows already ordered by table, ordinal)
        fields_by_table: dict[str, list[dict]] = defaultdict(list)
        for row in mirror_rows:
            fields_by_table[row.table_name].append(
                {"name": row.column_name, "type": row.data_type}
            )

        # Bulk load all matching pipelines to avoid N+1 per-table SELECTs.
        # Only id/task_id/schema_manually_edited are used below, and existing
        # fields are replaced via a bulk DELETE, so the fields relationship is
        # intentionally NOT eager-loaded.
        task_ids = list(fields_by_table.keys())
        stmt = select(Pipeline).where(Pipeline.task_id.in_(task_ids))
        result = await self.session.execute(stmt)
        pipeline_by_task_id = {p.task_id: p for p in result.scalars().all()}

        synced = 0
        # Collect all pipelines that have fields to sync for batch DELETE
        pipelines_to_sync: list[tuple] = []  # (pipeline, fields)
        for task_id, fields in fields_by_table.items():
            pipeline = pipeline_by_task_id.get(task_id)
            if not pipeline:
                logger.debug(
                    "No pipeline with task_id=%s — skipping table schema",
                    task_id,
                )
                continue
            # Skip pipelines with manually edited schemas
            if pipeline.schema_manually_edited:
                logger.debug(
                    "Pipeline %s has manually edited schema — skipping catalog sync",
                    pipeline.name,
                )
                continue
            if fields:
                pipelines_to_sync.append((pipeline, fields))

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
        logger.info("Projected catalog mirror onto %d pipelines", synced)
        return synced

    @staticmethod
    def _table_to_display_name(table_name: str) -> str:
        """Convert table name to display name.

        E.g., "shopify_sales_sync" -> "Shopify Sales Sync"
        """
        return table_name.replace("_", " ").title()
