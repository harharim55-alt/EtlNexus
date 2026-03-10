"""Repository for dag_tasks — cached Airflow DAG membership and task graph."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dag_task import DagTask


class DagTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, data: dict) -> DagTask:
        stmt = select(DagTask).where(
            DagTask.dag_id == data["dag_id"],
            DagTask.task_id == data["task_id"],
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()

        if row:
            for key, value in data.items():
                if hasattr(row, key):
                    setattr(row, key, value)
        else:
            row = DagTask(**data)
            self.session.add(row)

        await self.session.flush()
        return row

    async def get_dags_for_task(self, task_id: str) -> list[DagTask]:
        stmt = select(DagTask).where(DagTask.task_id == task_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_tasks_for_dag(self, dag_id: str) -> list[DagTask]:
        stmt = select(DagTask).where(DagTask.dag_id == dag_id)
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

    async def delete_stale(self, current_dag_task_pairs: set[tuple[str, str]]) -> int:
        """Delete rows not in the current set of (dag_id, task_id) pairs."""
        all_stmt = select(DagTask)
        result = await self.session.execute(all_stmt)
        all_rows = list(result.scalars().all())

        deleted = 0
        for row in all_rows:
            if (row.dag_id, row.task_id) not in current_dag_task_pairs:
                await self.session.delete(row)
                deleted += 1

        if deleted:
            await self.session.flush()
        return deleted
