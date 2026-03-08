import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.airflow_status import AirflowRunStatus


class AirflowRepository:
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
        pipeline_id = data["pipeline_id"]
        stmt = select(AirflowRunStatus).where(
            AirflowRunStatus.pipeline_id == pipeline_id
        )
        result = await self.session.execute(stmt)
        status = result.scalar_one_or_none()

        if status:
            for key, value in data.items():
                if hasattr(status, key):
                    setattr(status, key, value)
        else:
            status = AirflowRunStatus(**data)
            self.session.add(status)

        await self.session.flush()
        return status
