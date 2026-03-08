import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline_usage import PipelineUsage


class UsageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_pipeline_id(self, pipeline_id: uuid.UUID) -> list[PipelineUsage]:
        stmt = (
            select(PipelineUsage)
            .where(PipelineUsage.pipeline_id == pipeline_id)
            .order_by(PipelineUsage.access_count.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
