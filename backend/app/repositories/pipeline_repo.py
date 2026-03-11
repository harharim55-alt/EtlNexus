import uuid
from datetime import datetime, timedelta

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pipeline import Pipeline, PipelineField
from app.models.run_history import PipelineRunHistory
from app.models.visibility_grant import VisibilityGrant


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
        pattern = f"%{query}%"
        # Search across pipeline name, description, and field names
        field_subq = (
            select(PipelineField.pipeline_id)
            .where(PipelineField.name.ilike(pattern))
            .distinct()
            .scalar_subquery()
        )
        stmt = (
            select(Pipeline)
            .options(selectinload(Pipeline.airflow_status))
            .where(
                or_(
                    Pipeline.name.ilike(pattern),
                    Pipeline.description.ilike(pattern),
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

        if pipeline:
            for key, value in data.items():
                if key != "name" and hasattr(pipeline, key):
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
        cutoff = datetime.utcnow() - timedelta(days=30)
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
    ) -> Pipeline | None:
        pipeline = await self.get_by_id(pipeline_id)
        if not pipeline:
            return None
        if description is not None:
            pipeline.description = description
        if documentation is not None:
            pipeline.documentation = documentation
        pipeline.last_updated_by = updated_by
        pipeline.last_updated_at = datetime.utcnow()
        await self.session.commit()
        return pipeline

    async def list_visible(
        self,
        *,
        user_id: uuid.UUID | None = None,
        user_team_ids: set[uuid.UUID] | None = None,
        is_admin: bool = False,
        query: str | None = None,
    ) -> list[Pipeline]:
        """Return pipelines filtered by team visibility + optional text search."""
        base = (
            select(Pipeline)
            .options(selectinload(Pipeline.airflow_status))
        )

        if query:
            pattern = f"%{query}%"
            field_subq = (
                select(PipelineField.pipeline_id)
                .where(PipelineField.name.ilike(pattern))
                .distinct()
                .scalar_subquery()
            )
            base = base.where(
                or_(
                    Pipeline.name.ilike(pattern),
                    Pipeline.description.ilike(pattern),
                    Pipeline.id.in_(field_subq),
                )
            )

        if not is_admin:
            visibility_conditions = [Pipeline.team_id.is_(None)]

            # Team-based visibility: user's own teams
            if user_team_ids:
                visibility_conditions.append(Pipeline.team_id.in_(user_team_ids))

                # Grants targeting user's teams → specific pipeline
                visibility_conditions.append(
                    Pipeline.id.in_(
                        select(VisibilityGrant.pipeline_id)
                        .where(
                            VisibilityGrant.grantee_team_id.in_(user_team_ids),
                            VisibilityGrant.pipeline_id.isnot(None),
                        )
                        .scalar_subquery()
                    )
                )
                # Grants targeting user's teams → all pipelines of a source team
                visibility_conditions.append(
                    Pipeline.team_id.in_(
                        select(VisibilityGrant.source_team_id)
                        .where(
                            VisibilityGrant.grantee_team_id.in_(user_team_ids),
                            VisibilityGrant.source_team_id.isnot(None),
                        )
                        .scalar_subquery()
                    )
                )

            # Grants targeting specific user → specific pipeline
            if user_id:
                visibility_conditions.append(
                    Pipeline.id.in_(
                        select(VisibilityGrant.pipeline_id)
                        .where(
                            VisibilityGrant.grantee_user_id == user_id,
                            VisibilityGrant.pipeline_id.isnot(None),
                        )
                        .scalar_subquery()
                    )
                )
                # Grants targeting specific user → all pipelines of a source team
                visibility_conditions.append(
                    Pipeline.team_id.in_(
                        select(VisibilityGrant.source_team_id)
                        .where(
                            VisibilityGrant.grantee_user_id == user_id,
                            VisibilityGrant.source_team_id.isnot(None),
                        )
                        .scalar_subquery()
                    )
                )

            base = base.where(or_(*visibility_conditions))

        base = base.order_by(Pipeline.name).limit(200)
        result = await self.session.execute(base)
        return list(result.scalars().all())

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

    async def get_all_with_fields(self) -> list[Pipeline]:
        stmt = (
            select(Pipeline)
            .options(selectinload(Pipeline.fields))
            .order_by(Pipeline.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
