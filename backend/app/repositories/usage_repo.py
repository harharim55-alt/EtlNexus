from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline_usage import PipelineUsage


class UsageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_etl_name(
        self,
        etl_name: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[PipelineUsage]:
        conditions = [PipelineUsage.etl_name == etl_name]
        if date_from:
            conditions.append(PipelineUsage.last_accessed_at >= date_from)
        if date_to:
            conditions.append(PipelineUsage.last_accessed_at <= date_to)
        stmt = (
            select(PipelineUsage)
            .where(*conditions)
            .order_by(PipelineUsage.access_count.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_enrichment_map(
        self,
        etl_name: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, PipelineUsage]:
        """Return usage records keyed by consumer_name for enrichment lookup.

        Keys are stored as-is (consumer_name matches the task_id format used
        in dag_tasks, e.g. PascalCase like 'BgpRouteSync').
        """
        usages = await self.get_by_etl_name(etl_name, date_from=date_from, date_to=date_to)
        return {u.consumer_name: u for u in usages}
