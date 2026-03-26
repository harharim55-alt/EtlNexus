"""Repository for dag_tasks — cached Airflow DAG membership and task graph."""


from sqlalchemy import delete, distinct, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dag_task import DagTask
from app.repositories.base import UpsertMixin


class DagTaskRepository(UpsertMixin):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, data: dict) -> DagTask:
        return await self._upsert(
            DagTask,
            lookup_kwargs={"dag_id": data["dag_id"], "task_id": data["task_id"]},
            data=data,
        )

    async def get_dags_for_task(self, task_id: str) -> list[DagTask]:
        stmt = select(DagTask).where(DagTask.task_id == task_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_tasks_for_dag(self, dag_id: str) -> list[DagTask]:
        stmt = select(DagTask).where(DagTask.dag_id == dag_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_tasks_for_dag_with_pipeline(self, dag_id: str) -> list[DagTask]:
        stmt = (
            select(DagTask)
            .where(DagTask.dag_id == dag_id)
            .options(selectinload(DagTask.pipeline))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_downstream_of(self, task_id: str) -> list[DagTask]:
        """Find all DagTask rows where task_id appears in another row's downstream_task_ids."""
        # Get all rows where this task_id has downstream tasks
        stmt = select(DagTask).where(DagTask.task_id == task_id)
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())

        downstream_task_ids: set[str] = set()
        for row in rows:
            downstream_task_ids.update(row.downstream_task_ids or [])

        if not downstream_task_ids:
            return []

        # Return DagTask rows for those downstream task_ids (deduplicated by task_id)
        stmt = select(DagTask).where(DagTask.task_id.in_(downstream_task_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_dag_ids(self) -> list[str]:
        stmt = select(distinct(DagTask.dag_id)).order_by(DagTask.dag_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_tasks_per_dag(self) -> dict[str, int]:
        stmt = (
            select(DagTask.dag_id, func.count().label("cnt"))
            .group_by(DagTask.dag_id)
        )
        result = await self.session.execute(stmt)
        return {row.dag_id: row.cnt for row in result.all()}

    async def count_pipelines_per_dag(self) -> dict[str, int]:
        stmt = (
            select(DagTask.dag_id, func.count().label("cnt"))
            .where(DagTask.pipeline_id.isnot(None))
            .group_by(DagTask.dag_id)
        )
        result = await self.session.execute(stmt)
        return {row.dag_id: row.cnt for row in result.all()}

    async def get_all_entries(self) -> list[DagTask]:
        stmt = select(DagTask)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_stale(self, current_dag_task_pairs: set[tuple[str, str]]) -> int:
        """Delete rows not in the current set of (dag_id, task_id) pairs."""
        if not current_dag_task_pairs:
            # No current pairs — delete everything
            result = await self.session.execute(delete(DagTask))
            await self.session.flush()
            return result.rowcount  # type: ignore[return-value]

        # Bulk DELETE using composite key NOT IN
        stmt = delete(DagTask).where(
            ~tuple_(DagTask.dag_id, DagTask.task_id).in_(
                list(current_dag_task_pairs)
            )
        )
        result = await self.session.execute(stmt)
        if result.rowcount:
            await self.session.flush()
        return result.rowcount  # type: ignore[return-value]
