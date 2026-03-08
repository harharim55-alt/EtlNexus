from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline_usage import PipelineUsage


class UsageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_etl_name(self, etl_name: str) -> list[PipelineUsage]:
        stmt = (
            select(PipelineUsage)
            .where(PipelineUsage.etl_name == etl_name)
            .order_by(PipelineUsage.access_count.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_enrichment_map(self, etl_name: str) -> dict[str, PipelineUsage]:
        """Return usage records keyed by normalized consumer_name for enrichment lookup."""
        usages = await self.get_by_etl_name(etl_name)
        return {
            u.consumer_name.lower().replace(" ", "_").replace("-", "_"): u
            for u in usages
        }
