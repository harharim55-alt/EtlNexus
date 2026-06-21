import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cache import task_id_map_cache
from app.models.data_product_table import DataProductTable
from app.models.pipeline import Pipeline, PipelineField
from app.repositories.base import apply_updates

_UNSET = object()


def _escape_like(value: str) -> str:
    """Escape LIKE special characters so they are treated as literals."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class PipelineRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, *, skip: int = 0, limit: int = 200) -> list[Pipeline]:
        stmt = (
            select(Pipeline)
            .order_by(Pipeline.name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_task_id_map(self) -> dict[str, SimpleNamespace]:
        """Return a lightweight {task_id: summary} map without eager-loading relationships.

        Each value is a SimpleNamespace with .id, .name, .task_id, .description,
        .team — sufficient for AI catalog context lookups.

        Results are cached via task_id_map_cache (short TTL, cleared on sync).
        """
        cache_key = "task_id_map"
        cached = task_id_map_cache.get(cache_key)
        if cached is not None:
            return cached

        stmt = (
            select(
                Pipeline.id,
                Pipeline.name,
                Pipeline.task_id,
                Pipeline.description,
                Pipeline.team,
            )
            .where(Pipeline.task_id.isnot(None))
        )
        result = await self.session.execute(stmt)
        pipeline_map = {
            row.task_id: SimpleNamespace(
                id=row.id,
                name=row.name,
                task_id=row.task_id,
                description=row.description,
                team=row.team,
            )
            for row in result.all()
        }
        task_id_map_cache.set(cache_key, pipeline_map)
        return pipeline_map

    async def get_product_tables(self, product_id: uuid.UUID) -> list[DataProductTable]:
        """Tables (namespace, table_name) a data product references, ordered."""
        stmt = (
            select(DataProductTable)
            .where(DataProductTable.product_id == product_id)
            .order_by(DataProductTable.namespace, DataProductTable.table_name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_tables_for_products(
        self, product_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[DataProductTable]]:
        """Batch-fetch referenced tables for many products: {product_id: [tables]}."""
        if not product_ids:
            return {}
        stmt = (
            select(DataProductTable)
            .where(DataProductTable.product_id.in_(product_ids))
            .order_by(DataProductTable.namespace, DataProductTable.table_name)
        )
        result = await self.session.execute(stmt)
        out: dict[uuid.UUID, list[DataProductTable]] = {}
        for row in result.scalars().all():
            out.setdefault(row.product_id, []).append(row)
        return out

    async def set_product_tables(
        self, product_id: uuid.UUID, tables: list[tuple[str, str]]
    ) -> None:
        """Replace a data product's referenced tables (delete-all then re-add, deduped)."""
        await self.session.execute(
            delete(DataProductTable).where(DataProductTable.product_id == product_id)
        )
        seen: set[tuple[str, str]] = set()
        for namespace, table_name in tables:
            key = (namespace, table_name)
            if key in seen:
                continue
            seen.add(key)
            self.session.add(
                DataProductTable(product_id=product_id, namespace=namespace, table_name=table_name)
            )
        await self.session.flush()

    async def get_by_id(self, pipeline_id: uuid.UUID) -> Pipeline | None:
        stmt = (
            select(Pipeline)
            .options(
                selectinload(Pipeline.fields),
            )
            .where(Pipeline.id == pipeline_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(self, query: str) -> list[Pipeline]:
        pattern = f"%{_escape_like(query)}%"
        # Search across pipeline name, description, and field names
        field_subq = (
            select(PipelineField.pipeline_id)
            .where(PipelineField.name.ilike(pattern, escape="\\"))
            .distinct()
            .scalar_subquery()
        )
        stmt = (
            select(Pipeline)
            .where(
                or_(
                    Pipeline.name.ilike(pattern, escape="\\"),
                    Pipeline.description.ilike(pattern, escape="\\"),
                    Pipeline.id.in_(field_subq),
                )
            )
            .order_by(Pipeline.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(self, data: dict) -> Pipeline:
        name = data["name"]
        stmt = select(Pipeline).where(Pipeline.name == name)
        result = await self.session.execute(stmt)
        pipeline = result.scalar_one_or_none()

        # Fallback: match by task_id if name lookup missed
        if not pipeline and data.get("task_id"):
            stmt2 = select(Pipeline).where(Pipeline.task_id == data["task_id"])
            result2 = await self.session.execute(stmt2)
            pipeline = result2.scalar_one_or_none()

        if pipeline:
            def _skip_user_edited(m, k, v):
                return not (k == "description" and m.description_edited_by_user)

            apply_updates(pipeline, data, exclude_keys={"name"}, condition_fn=_skip_user_edited)
        else:
            pipeline = Pipeline(**data)
            self.session.add(pipeline)

        await self.session.flush()
        return pipeline

    async def bulk_upsert_pipelines(self, entries: list[dict]) -> dict[str, Pipeline]:
        """Batch upsert pipelines in two SELECT + one INSERT round-trip.

        Replaces N sequential ``upsert()`` calls with:
        1. One SELECT by all names.
        2. One SELECT by task_id for any entries not matched by name.
        3. In-memory ORM updates for existing rows (preserving ``description_edited_by_user``).
        4. One ``INSERT … ON CONFLICT DO NOTHING`` for genuinely new pipelines.
        5. A single flush.

        Args:
            entries: List of pipeline data dicts, each containing at least
                ``name`` and optionally ``task_id``, ``description``,
                ``category``, and ``schedule``.

        Returns:
            Mapping of ``task_id -> Pipeline`` for every entry that has a
            ``task_id`` value.  Entries without a ``task_id`` are excluded.
        """
        if not entries:
            return {}

        def _skip_user_edited(m: Pipeline, k: str, v: object) -> bool:
            return not (k == "description" and m.description_edited_by_user)

        # --- Step 1: batch-fetch by name ---
        names = [d["name"] for d in entries]
        stmt = select(Pipeline).where(Pipeline.name.in_(names))
        result = await self.session.execute(stmt)
        by_name: dict[str, Pipeline] = {p.name: p for p in result.scalars().all()}

        # --- Step 2: batch-fetch by task_id for entries not matched by name ---
        unmatched_task_ids = [
            d["task_id"]
            for d in entries
            if d["name"] not in by_name and d.get("task_id")
        ]
        by_task_id: dict[str, Pipeline] = {}
        if unmatched_task_ids:
            stmt2 = select(Pipeline).where(Pipeline.task_id.in_(unmatched_task_ids))
            result2 = await self.session.execute(stmt2)
            by_task_id = {p.task_id: p for p in result2.scalars().all() if p.task_id}

        # --- Step 3: separate updates vs new inserts ---
        new_values: list[dict] = []
        new_pipeline_data: list[dict] = []  # Kept for post-insert re-fetch by name

        for data in entries:
            existing = by_name.get(data["name"]) or by_task_id.get(data.get("task_id", ""))
            if existing:
                apply_updates(existing, data, exclude_keys={"name"}, condition_fn=_skip_user_edited)
            else:
                row = {k: v for k, v in data.items()}
                row.setdefault("id", uuid.uuid4())
                new_values.append(row)
                new_pipeline_data.append(data)

        # --- Step 4: bulk INSERT new rows, ignoring conflicts on name ---
        if new_values:
            insert_stmt = pg_insert(Pipeline).values(new_values)
            insert_stmt = insert_stmt.on_conflict_do_nothing(index_elements=["name"])
            await self.session.execute(insert_stmt)

        # --- Step 5: single flush to materialise all changes ---
        await self.session.flush()

        # --- Step 6: re-fetch newly inserted rows so ORM objects are live ---
        if new_pipeline_data:
            new_names = [d["name"] for d in new_pipeline_data]
            refetch_stmt = select(Pipeline).where(Pipeline.name.in_(new_names))
            refetch_result = await self.session.execute(refetch_stmt)
            for p in refetch_result.scalars().all():
                by_name[p.name] = p

        # --- Build task_id -> Pipeline return map ---
        task_id_map: dict[str, Pipeline] = {}
        for data in entries:
            tid = data.get("task_id")
            if not tid:
                continue
            pipeline = by_name.get(data["name"]) or by_task_id.get(tid)
            if pipeline:
                task_id_map[tid] = pipeline
        return task_id_map

    async def bulk_set_teams(
        self,
        assignments: list[tuple[uuid.UUID, str, uuid.UUID]],
    ) -> None:
        """Batch update team assignments for multiple pipelines.

        Applies ORM-level updates in memory and issues a single flush, which
        collapses all dirty-row writes into one database round-trip.

        Args:
            assignments: List of ``(pipeline_id, team_name, team_id)`` tuples.
                Pipelines absent from the session identity map are skipped
                (they were never loaded, so there is nothing to update here —
                the caller is responsible for ensuring pipelines are in-session).
        """
        if not assignments:
            return

        # Build a lookup so we can match loaded ORM objects by primary key.
        pipeline_ids = [pid for pid, _, _ in assignments]
        stmt = select(Pipeline).where(Pipeline.id.in_(pipeline_ids))
        result = await self.session.execute(stmt)
        by_id: dict[uuid.UUID, Pipeline] = {p.id: p for p in result.scalars().all()}

        for pipeline_id, team_name, team_id in assignments:
            pipeline = by_id.get(pipeline_id)
            if pipeline:
                pipeline.team = team_name
                pipeline.team_id = team_id

        await self.session.flush()

    async def get_by_task_id(self, task_id: str) -> Pipeline | None:
        stmt = select(Pipeline).where(Pipeline.task_id == task_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_metadata(
        self,
        pipeline_id: uuid.UUID,
        *,
        name=_UNSET,
        description=_UNSET,
        documentation=_UNSET,
        import_snippet=_UNSET,
        schedule_type=_UNSET,
        updated_by: str = "System",
        pipeline: "Pipeline | None" = None,
        set_description_edited: bool = False,
    ) -> Pipeline | None:
        if pipeline is None:
            pipeline = await self.get_by_id(pipeline_id)
        if not pipeline:
            return None
        if name is not _UNSET and name:
            pipeline.name = name
        if description is not _UNSET:
            pipeline.description = description
            if set_description_edited:
                pipeline.description_edited_by_user = True
        if documentation is not _UNSET:
            pipeline.documentation = documentation
        if import_snippet is not _UNSET:
            pipeline.import_snippet = import_snippet
        if schedule_type is not _UNSET:
            pipeline.schedule_type = schedule_type
        pipeline.last_updated_by = updated_by
        pipeline.last_updated_at = datetime.now(UTC)
        await self.session.flush()
        return pipeline

    async def delete(self, pipeline_id: uuid.UUID) -> bool:
        """Delete a pipeline (cascades to its fields, tables, revisions)."""
        pipeline = await self.get_by_id(pipeline_id)
        if not pipeline:
            return False
        await self.session.delete(pipeline)
        await self.session.flush()
        return True

    async def list_visible(
        self,
        *,
        user_id: uuid.UUID | None = None,
        user_team_ids: set[uuid.UUID] | None = None,
        is_admin: bool = False,
        query: str | None = None,
        skip: int = 0,
        limit: int = 200,
        team_names: list[str] | None = None,
        schedule_types: list[str] | None = None,
        is_data_product: bool | None = None,
    ) -> tuple[list[Pipeline], int]:
        """Return pipelines filtered by team visibility + optional text search.

        Returns (pipelines, total_count) where total_count is the full
        count before offset/limit pagination.
        """
        conditions = []

        if query:
            pattern = f"%{_escape_like(query)}%"
            field_subq = (
                select(PipelineField.pipeline_id)
                .where(PipelineField.name.ilike(pattern, escape="\\"))
                .distinct()
                .scalar_subquery()
            )
            conditions.append(
                or_(
                    Pipeline.name.ilike(pattern, escape="\\"),
                    Pipeline.description.ilike(pattern, escape="\\"),
                    Pipeline.id.in_(field_subq),
                )
            )

        # Server-side filters: team, schedule
        if team_names:
            conditions.append(Pipeline.team.in_(team_names))

        if schedule_types:
            conditions.append(Pipeline.schedule_type.in_(schedule_types))

        if is_data_product is not None:
            conditions.append(Pipeline.is_data_product == is_data_product)

        # All products are visible to every authenticated user (edit is gated
        # separately by team membership). No view-time team scoping.

        # Count total matching rows (without offset/limit)
        count_stmt = select(func.count()).select_from(Pipeline)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        # Fetch paginated data
        data_stmt = (
            select(Pipeline)
            .order_by(Pipeline.name)
            .offset(skip)
            .limit(limit)
        )
        if conditions:
            data_stmt = data_stmt.where(*conditions)
        result = await self.session.execute(data_stmt)
        return list(result.scalars().all()), total

    async def set_team(
        self,
        pipeline_id: uuid.UUID,
        team_name: str,
        team_id: uuid.UUID,
    ) -> None:
        """Set the team ownership on a pipeline."""
        pipeline = await self.get_by_id(pipeline_id)
        if pipeline:
            pipeline.team = team_name
            pipeline.team_id = team_id
            await self.session.flush()

    async def get_by_team_id(self, team_id: uuid.UUID) -> list[Pipeline]:
        """Return pipelines owned by a specific team (uses ix_pipelines_team_id index)."""
        stmt = (
            select(Pipeline)
            .where(Pipeline.team_id == team_id)
            .order_by(Pipeline.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_with_fields(self) -> list[Pipeline]:
        stmt = (
            select(Pipeline)
            .options(selectinload(Pipeline.fields))
            .order_by(Pipeline.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_shared_field_pipelines(
        self, pipeline_id: uuid.UUID
    ) -> list[dict]:
        """Find pipelines sharing field names with the given pipeline via SQL.

        Uses GROUP BY + array_agg instead of loading all pipelines+fields into memory.
        Returns list of dicts with pipeline_id, pipeline_name, shared_fields.
        """
        # Subquery: field names for the target pipeline
        my_fields = (
            select(PipelineField.name)
            .where(PipelineField.pipeline_id == pipeline_id)
            .scalar_subquery()
        )

        # Find other pipelines sharing those field names
        stmt = (
            select(
                Pipeline.id.label("pipeline_id"),
                Pipeline.name.label("pipeline_name"),
                func.array_agg(PipelineField.name).label("shared_fields"),
            )
            .join(PipelineField, PipelineField.pipeline_id == Pipeline.id)
            .where(
                PipelineField.name.in_(my_fields),
                Pipeline.id != pipeline_id,
            )
            .group_by(Pipeline.id, Pipeline.name)
            .order_by(func.count(PipelineField.name).desc())
        )
        result = await self.session.execute(stmt)
        return [
            {
                "pipeline_id": row.pipeline_id,
                "pipeline_name": row.pipeline_name,
                "shared_fields": sorted(row.shared_fields),
            }
            for row in result.all()
        ]

