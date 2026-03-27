import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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

    async def bulk_upsert(self, entries: list[dict]) -> int:
        """Batch upsert airflow run statuses using INSERT ... ON CONFLICT."""
        if not entries:
            return 0
        for entry in entries:
            entry.setdefault("id", uuid.uuid4())
        stmt = pg_insert(AirflowRunStatus).values(entries)
        stmt = stmt.on_conflict_do_update(
            index_elements=["pipeline_id"],
            set_={
                "dag_id": stmt.excluded.dag_id,
                "status": stmt.excluded.status,
                "execution_date": stmt.excluded.execution_date,
                "last_checked_at": stmt.excluded.last_checked_at,
            },
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
