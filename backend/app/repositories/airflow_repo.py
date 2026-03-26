import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.airflow_status import AirflowRunStatus
from app.repositories.base import UpsertMixin


class AirflowRepository(UpsertMixin):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> list[AirflowRunStatus]:
        stmt = select(AirflowRunStatus)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_pipeline_id(self, pipeline_id: uuid.UUID) -> AirflowRunStatus | None:
        stmt = select(AirflowRunStatus).where(
            AirflowRunStatus.pipeline_id == pipeline_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, data: dict) -> AirflowRunStatus:
        return await self._upsert(
            AirflowRunStatus,
            lookup_kwargs={"pipeline_id": data["pipeline_id"]},
            data=data,
        )
