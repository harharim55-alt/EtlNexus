import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pipeline import Pipeline, PipelineField
from app.models.run_history import PipelineRunHistory
from app.models.visibility_grant import VisibilityGrant


def _escape_like(value: str) -> str:
    """Escape LIKE special characters so they are treated as literals."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class PipelineRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, *, skip: int = 0, limit: int = 200) -> list[Pipeline]:
        stmt = (
            select(Pipeline)
            .options(selectinload(Pipeline.airflow_status))
            .order_by(Pipeline.name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, pipeline_id: uuid.UUID) -> Pipeline | None:
        stmt = (
            select(Pipeline)
            .options(
                selectinload(Pipeline.fields),
                selectinload(Pipeline.airflow_status),
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
            .options(selectinload(Pipeline.airflow_status))
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
            for key, value in data.items():
                if key != "name" and hasattr(pipeline, key):
                    # Don't overwrite user-edited descriptions during Airflow sync
                    if key == "description" and pipeline.description_edited_by_user:
                        continue
                    setattr(pipeline, key, value)
        else:
            pipeline = Pipeline(**data)
            self.session.add(pipeline)

        await self.session.flush()
        return pipeline

    async def get_success_rates(
        self, pipeline_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, float]:
        """Compute 30-day success rate for a batch of pipelines."""
        if not pipeline_ids:
            return {}
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        stmt = (
            select(
                PipelineRunHistory.pipeline_id,
                func.count().label("total"),
                func.sum(
                    case((PipelineRunHistory.status == "success", 1), else_=0)
                ).label("successes"),
            )
            .where(
                PipelineRunHistory.pipeline_id.in_(pipeline_ids),
                PipelineRunHistory.duration_seconds.isnot(None),
                PipelineRunHistory.start_date >= cutoff,
            )
            .group_by(PipelineRunHistory.pipeline_id)
        )
        result = await self.session.execute(stmt)
        rates: dict[uuid.UUID, float] = {}
        for row in result.all():
            if row.total > 0:
                rates[row.pipeline_id] = round(
                    (row.successes / row.total) * 100, 1
                )
        return rates

    async def get_by_task_id(self, task_id: str) -> Pipeline | None:
        stmt = select(Pipeline).where(Pipeline.task_id == task_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_metadata(
        self,
        pipeline_id: uuid.UUID,
        *,
        description: str | None = None,
        documentation: str | None = None,
        updated_by: str = "System",
        pipeline: "Pipeline | None" = None,
        set_description_edited: bool = False,
    ) -> Pipeline | None:
        if pipeline is None:
            pipeline = await self.get_by_id(pipeline_id)
        if not pipeline:
            return None
        if description is not None:
            pipeline.description = description
            if set_description_edited:
                pipeline.description_edited_by_user = True
        if documentation is not None:
            pipeline.documentation = documentation
        pipeline.last_updated_by = updated_by
        pipeline.last_updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return pipeline

    async def list_visible(
        self,
        *,
        user_id: uuid.UUID | None = None,
        user_team_ids: set[uuid.UUID] | None = None,
        is_admin: bool = False,
        query: str | None = None,
        skip: int = 0,
        limit: int = 200,
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

        if not is_admin:
            visibility_conditions = [Pipeline.team_id.is_(None)]

            if user_team_ids:
                visibility_conditions.append(Pipeline.team_id.in_(user_team_ids))

            # Pre-fetch all grant-visible pipeline IDs and team IDs in one flat query
            # instead of 4 correlated subqueries
            grant_conditions = []
            if user_team_ids:
                grant_conditions.append(
                    VisibilityGrant.grantee_team_id.in_(user_team_ids)
                )
            if user_id:
                grant_conditions.append(
                    VisibilityGrant.grantee_user_id == user_id
                )

            if grant_conditions:
                grant_stmt = select(
                    VisibilityGrant.pipeline_id,
                    VisibilityGrant.source_team_id,
                ).where(or_(*grant_conditions))
                grant_result = await self.session.execute(grant_stmt)

                granted_pipeline_ids: set[uuid.UUID] = set()
                granted_source_team_ids: set[uuid.UUID] = set()
                for row in grant_result.all():
                    if row.pipeline_id:
                        granted_pipeline_ids.add(row.pipeline_id)
                    if row.source_team_id:
                        granted_source_team_ids.add(row.source_team_id)

                if granted_pipeline_ids:
                    visibility_conditions.append(
                        Pipeline.id.in_(granted_pipeline_ids)
                    )
                if granted_source_team_ids:
                    visibility_conditions.append(
                        Pipeline.team_id.in_(granted_source_team_ids)
                    )

            conditions.append(or_(*visibility_conditions))

        # Count total matching rows (without offset/limit)
        count_stmt = select(func.count()).select_from(Pipeline)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        # Fetch paginated data
        data_stmt = (
            select(Pipeline)
            .options(selectinload(Pipeline.airflow_status))
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
            .options(selectinload(Pipeline.airflow_status))
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
