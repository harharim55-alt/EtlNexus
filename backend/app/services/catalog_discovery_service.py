"""Catalog-driven pipeline discovery.

Replaces Airflow discovery when Airflow is disabled: creates one pipeline per
Iceberg table found in the catalog mirror (``catalog_columns``), so the registry
populates from Spark Connect. Idempotent — upserts by name/task_id and preserves
manual edits (``description_edited_by_user``).

Pipeline ``task_id`` is set to the table name so the existing field projection
(:class:`CatalogSyncService`) attaches each table's columns automatically.

Schedule (daily/hourly) is inferred lazily — only for pipelines that don't have
one yet — so the hot 30s mirror path stays cheap and an existing schedule is
never cleared by a transient failure.
"""

import asyncio
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.spark_connect_client import spark_connect_client
from app.models.pipeline import Pipeline
from app.repositories.catalog_mirror_repo import CatalogMirrorRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.team_repo import TeamRepository
from app.services.catalog_sync_service import CatalogSyncService

logger = logging.getLogger(__name__)


class CatalogDiscoveryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mirror_repo = CatalogMirrorRepository(session)
        self.pipeline_repo = PipelineRepository(session)
        self.team_repo = TeamRepository(session)

    async def discover(self) -> int:
        """Upsert one pipeline per catalog table. Returns the number of tables."""
        rows = await self.mirror_repo.list_all()
        if not rows:
            logger.info("Catalog mirror empty — no pipelines to discover")
            return 0

        # Distinct table -> namespace (first occurrence wins)
        table_ns: dict[str, str] = {}
        for row in rows:
            table_ns.setdefault(row.table_name, row.namespace)

        # Resolve (or create) a team per namespace so RBAC visibility works
        team_id_by_ns: dict[str, object] = {}
        team_name_by_ns: dict[str, str] = {}
        for ns in set(table_ns.values()):
            team = await self.team_repo.get_or_create(ns.capitalize(), source="catalog")
            team_id_by_ns[ns] = team.id
            team_name_by_ns[ns] = team.name

        # Keep keys identical across all entries — bulk_upsert_pipelines does a
        # single multi-row INSERT that takes its columns from the first dict.
        # category is intentionally None: for catalog-discovered pipelines the
        # namespace already maps to `team`, so a category badge would just repeat
        # it (e.g. "PRISM prism"). None also clears it on existing rows.
        entries = [
            {
                "name": CatalogSyncService._table_to_display_name(table_name),
                "task_id": table_name,
                "team": team_name_by_ns[ns],
                "team_id": team_id_by_ns[ns],
                "category": None,
            }
            for table_name, ns in table_ns.items()
        ]
        await self.pipeline_repo.bulk_upsert_pipelines(entries)
        await self.session.commit()

        await self._infer_missing_schedules(table_ns)
        await self._promote_data_products(list(table_ns.keys()))

        logger.info(
            "Catalog discovery: upserted %d pipelines from %d catalog tables",
            len(entries), len(table_ns),
        )
        return len(entries)

    async def _promote_data_products(self, table_names: list[str]) -> None:
        """Auto-promote curated outputs (by name pattern) to data products.

        Only ever sets ``is_data_product=True`` for matches, so manual promotions
        of other pipelines are preserved.
        """
        patterns = [p.strip().lower() for p in settings.data_product_name_patterns.split(",") if p.strip()]
        if not patterns:
            return
        matches = [t for t in table_names if any(p in t.lower() for p in patterns)]
        if not matches:
            return
        result = await self.session.execute(
            update(Pipeline)
            .where(Pipeline.task_id.in_(matches), Pipeline.is_data_product.is_(False))
            .values(is_data_product=True)
        )
        if result.rowcount:
            await self.session.commit()
            logger.info("Catalog discovery: promoted %d pipelines to data products", result.rowcount)

    async def _infer_missing_schedules(self, table_ns: dict[str, str]) -> None:
        """Detect daily/hourly only for catalog pipelines that don't have a schedule.

        Steady state this does zero Spark calls (all already scheduled). Schedules
        are only ever set, never cleared, so a transient detection failure can't
        wipe a known cadence.
        """
        result = await self.session.execute(
            select(Pipeline.task_id).where(
                Pipeline.task_id.in_(list(table_ns.keys())),
                Pipeline.schedule.is_(None),
            )
        )
        pending = [tid for (tid,) in result.all() if tid]
        if not pending:
            return

        updated = 0
        for table_name in pending:
            schedule = await asyncio.to_thread(
                spark_connect_client.detect_schedule, table_ns[table_name], table_name
            )
            if schedule:
                await self.session.execute(
                    update(Pipeline)
                    .where(Pipeline.task_id == table_name)
                    .values(schedule=schedule)
                )
                updated += 1
        if updated:
            await self.session.commit()
            logger.info("Catalog discovery: inferred schedule for %d pipelines", updated)
