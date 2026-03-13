import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline_revision import PipelineRevision


class RevisionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        pipeline_id: uuid.UUID,
        field_name: str,
        content: str | None,
        changed_by: str,
        change_source: str = "user",
    ) -> PipelineRevision:
        """Snapshot the previous value of a field before it changes."""
        revision = PipelineRevision(
            pipeline_id=pipeline_id,
            field_name=field_name,
            content=content,
            changed_by=changed_by,
            change_source=change_source,
        )
        self.session.add(revision)
        await self.session.flush()
        return revision

    async def list_by_pipeline(
        self,
        pipeline_id: uuid.UUID,
        field_name: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[PipelineRevision], int]:
        conditions = [PipelineRevision.pipeline_id == pipeline_id]
        if field_name:
            conditions.append(PipelineRevision.field_name == field_name)

        count_stmt = (
            select(func.count()).select_from(PipelineRevision).where(*conditions)
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        data_stmt = (
            select(PipelineRevision)
            .where(*conditions)
            .order_by(PipelineRevision.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(data_stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, revision_id: uuid.UUID) -> PipelineRevision | None:
        stmt = select(PipelineRevision).where(PipelineRevision.id == revision_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
