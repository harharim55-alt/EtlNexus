import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pipeline import Pipeline, PipelineField


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

    async def get_all_with_fields(self) -> list[Pipeline]:
        stmt = (
            select(Pipeline)
            .options(selectinload(Pipeline.fields))
            .order_by(Pipeline.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
