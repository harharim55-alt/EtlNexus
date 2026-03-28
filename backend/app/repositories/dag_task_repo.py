"""Repository for dag_tasks — cached Airflow DAG membership and task graph."""

import uuid

from sqlalchemy import delete, distinct, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
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

    async def get_tasks_for_dags_with_pipeline(
        self, dag_ids: list[str]
    ) -> dict[str, list[DagTask]]:
        """Load DagTask rows for multiple DAGs with their pipeline eagerly loaded.

        Performs a single query using ``dag_id IN (...)`` with a
        ``selectinload`` for the pipeline relationship, then groups results by
        dag_id.

        Returns a dict keyed by dag_id.  DAGs with no tasks are absent from the
        result; callers should fall back to an empty list.
        """
        if not dag_ids:
            return {}

        stmt = (
            select(DagTask)
            .where(DagTask.dag_id.in_(dag_ids))
            .options(selectinload(DagTask.pipeline))
        )
        result = await self.session.execute(stmt)
        tasks = result.scalars().all()

        out: dict[str, list[DagTask]] = {}
        for task in tasks:
            out.setdefault(task.dag_id, []).append(task)
        return out

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

    async def get_dag_ids_for_pipelines(
        self, pipeline_ids: set[uuid.UUID]
    ) -> set[str]:
        """Return the set of DAG IDs that contain at least one of the given pipelines.

        Used to restrict the DAG summary list to DAGs visible to a non-admin user.
        """
        if not pipeline_ids:
            return set()
        stmt = (
            select(distinct(DagTask.dag_id))
            .where(DagTask.pipeline_id.in_(pipeline_ids))
        )
        result = await self.session.execute(stmt)
        return {row[0] for row in result.all()}

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

    async def get_entries_for_dags(self, dag_ids: list[str]) -> list[DagTask]:
        """Load dag_task entries only for the specified DAG IDs."""
        if not dag_ids:
            return []
        stmt = select(DagTask).where(DagTask.dag_id.in_(dag_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_upsert(self, entries: list[dict]) -> int:
        """Bulk upsert dag_task entries using INSERT ... ON CONFLICT DO UPDATE.

        Processes in chunks to stay within PostgreSQL parameter limits.
        Returns the total number of rows affected.
        """
        if not entries:
            return 0
        total = 0
        chunk_size = 500
        for i in range(0, len(entries), chunk_size):
            chunk = entries[i:i + chunk_size]
            for entry in chunk:
                entry.setdefault("id", uuid.uuid4())
            stmt = pg_insert(DagTask).values(chunk)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_dag_task",
                set_={
                    "pipeline_id": stmt.excluded.pipeline_id,
                    "downstream_task_ids": stmt.excluded.downstream_task_ids,
                    "needs": stmt.excluded.needs,
                    "prefers": stmt.excluded.prefers,
                    "task_group_id": stmt.excluded.task_group_id,
                    "bouncer_name": stmt.excluded.bouncer_name,
                    "bouncer_id": stmt.excluded.bouncer_id,
                },
            )
            result = await self.session.execute(stmt)
            total += result.rowcount
        await self.session.flush()
        return total

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
