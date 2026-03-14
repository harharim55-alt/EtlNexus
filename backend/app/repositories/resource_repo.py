"""Repository for pipeline resource configs and run history."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Float, case, distinct, extract, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource_config import PipelineResourceConfig
from app.models.run_history import PipelineRunHistory
from app.repositories.base import apply_updates


class ResourceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Resource Configs (allocated) ---

    async def upsert_config(self, data: dict) -> PipelineResourceConfig:
        pipeline_id = data["pipeline_id"]
        dag_id = data["dag_id"]
        stmt = select(PipelineResourceConfig).where(
            PipelineResourceConfig.pipeline_id == pipeline_id,
            PipelineResourceConfig.dag_id == dag_id,
        )
        result = await self.session.execute(stmt)
        config = result.scalar_one_or_none()

        if config:
            apply_updates(config, data)
        else:
            config = PipelineResourceConfig(**data)
            self.session.add(config)

        await self.session.flush()
        return config

    async def get_configs_by_pipeline(
        self, pipeline_id: uuid.UUID
    ) -> list[PipelineResourceConfig]:
        stmt = (
            select(PipelineResourceConfig)
            .where(PipelineResourceConfig.pipeline_id == pipeline_id)
            .order_by(PipelineResourceConfig.is_dag_override, PipelineResourceConfig.dag_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # --- Run History (actual usage + duration) ---

    async def upsert_run(self, data: dict) -> bool:
        """Insert or update a run record (re-runs overwrite old data).

        On conflict (same pipeline_id + dag_id + dag_run_id), overwrites
        start_date/end_date/duration/status and clears actuals so they
        get re-fetched from logs for the new attempt.
        """
        stmt = pg_insert(PipelineRunHistory).values(**data)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_run_history_pipeline_dag_run",
            set_={
                "duration_seconds": stmt.excluded.duration_seconds,
                "start_date": stmt.excluded.start_date,
                "end_date": stmt.excluded.end_date,
                "status": stmt.excluded.status,
                # Clear actuals — they belong to the previous attempt
                "driver_memory_used_mb": None,
                "executor_memory_peak_mb": None,
                "cpu_utilization_pct": None,
                "executors_active": None,
                "spark_application_id": None,
                "executor_run_time_ms": None,
                "executor_cpu_time_ms": None,
                "jvm_gc_time_ms": None,
                "shuffle_read_bytes": None,
                "shuffle_write_bytes": None,
                "input_bytes": None,
                "output_bytes": None,
                "memory_bytes_spilled": None,
                "disk_bytes_spilled": None,
                "peak_execution_memory": None,
                "result_size_bytes": None,
                "num_tasks": None,
                "num_stages": None,
                "metrics_source": None,
                "execution_plan": None,
            },
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def update_run_actuals(
        self,
        pipeline_id: uuid.UUID,
        dag_id: str,
        dag_run_id: str,
        actuals: dict,
    ) -> None:
        """Update actual resource usage fields for an existing run."""
        stmt = select(PipelineRunHistory).where(
            PipelineRunHistory.pipeline_id == pipeline_id,
            PipelineRunHistory.dag_id == dag_id,
            PipelineRunHistory.dag_run_id == dag_run_id,
        )
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        if run:
            run.driver_memory_used_mb = actuals.get("driver_memory_used_mb")
            run.executor_memory_peak_mb = actuals.get("executor_memory_peak_mb")
            run.cpu_utilization_pct = actuals.get("cpu_utilization_pct")
            run.executors_active = actuals.get("executors_active")
            # sparkMeasure extended metrics
            run.spark_application_id = actuals.get("spark_application_id")
            run.executor_run_time_ms = actuals.get("executor_run_time_ms")
            run.executor_cpu_time_ms = actuals.get("executor_cpu_time_ms")
            run.jvm_gc_time_ms = actuals.get("jvm_gc_time_ms")
            run.shuffle_read_bytes = actuals.get("shuffle_read_bytes")
            run.shuffle_write_bytes = actuals.get("shuffle_write_bytes")
            run.input_bytes = actuals.get("input_bytes")
            run.output_bytes = actuals.get("output_bytes")
            run.memory_bytes_spilled = actuals.get("memory_bytes_spilled")
            run.disk_bytes_spilled = actuals.get("disk_bytes_spilled")
            run.peak_execution_memory = actuals.get("peak_execution_memory")
            run.result_size_bytes = actuals.get("result_size_bytes")
            run.num_tasks = actuals.get("num_tasks")
            run.num_stages = actuals.get("num_stages")
            run.metrics_source = actuals.get("metrics_source")
            run.execution_plan = actuals.get("execution_plan")
            await self.session.flush()

    async def get_latest_execution_plan(
        self, pipeline_id: uuid.UUID
    ) -> PipelineRunHistory | None:
        """Get the most recent successful run that has an execution plan."""
        stmt = (
            select(PipelineRunHistory)
            .where(
                PipelineRunHistory.pipeline_id == pipeline_id,
                PipelineRunHistory.execution_plan.isnot(None),
                PipelineRunHistory.status == "success",
            )
            .order_by(PipelineRunHistory.start_date.desc().nullslast())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_execution_plan_by_run(
        self, pipeline_id: uuid.UUID, dag_run_id: str
    ) -> PipelineRunHistory | None:
        """Get execution plan for a specific DAG run."""
        stmt = (
            select(PipelineRunHistory)
            .where(
                PipelineRunHistory.pipeline_id == pipeline_id,
                PipelineRunHistory.dag_run_id == dag_run_id,
                PipelineRunHistory.execution_plan.isnot(None),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_execution_plan_runs(
        self, pipeline_id: uuid.UUID, skip: int = 0, limit: int = 20
    ) -> tuple[list[dict], int]:
        """List runs that have an execution plan, paginated. Returns (items, total)."""
        conditions = [
            PipelineRunHistory.pipeline_id == pipeline_id,
            PipelineRunHistory.execution_plan.isnot(None),
            PipelineRunHistory.status == "success",
        ]

        count_stmt = (
            select(func.count())
            .select_from(PipelineRunHistory)
            .where(*conditions)
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            select(
                PipelineRunHistory.dag_run_id,
                PipelineRunHistory.dag_id,
                PipelineRunHistory.start_date,
                PipelineRunHistory.status,
            )
            .where(*conditions)
            .order_by(PipelineRunHistory.start_date.desc().nullslast())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items = [
            {
                "dag_run_id": row.dag_run_id,
                "dag_id": row.dag_id,
                "start_date": row.start_date.isoformat() if row.start_date else None,
                "status": row.status,
            }
            for row in result.all()
        ]
        return items, total

    async def has_null_actuals(
        self,
        pipeline_id: uuid.UUID,
        dag_id: str,
        dag_run_id: str,
    ) -> bool:
        """Check if a run exists but has NULL actual resource usage."""
        stmt = select(PipelineRunHistory.id).where(
            PipelineRunHistory.pipeline_id == pipeline_id,
            PipelineRunHistory.dag_id == dag_id,
            PipelineRunHistory.dag_run_id == dag_run_id,
            PipelineRunHistory.driver_memory_used_mb.is_(None),
            PipelineRunHistory.status == "success",
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_recent_runs(
        self,
        pipeline_id: uuid.UUID,
        limit: int = 20,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[PipelineRunHistory]:
        conditions = [PipelineRunHistory.pipeline_id == pipeline_id]
        if date_from:
            conditions.append(PipelineRunHistory.start_date >= date_from)
        if date_to:
            conditions.append(PipelineRunHistory.start_date <= date_to)

        stmt = (
            select(PipelineRunHistory)
            .where(*conditions)
            .order_by(PipelineRunHistory.start_date.desc().nullslast())
        )
        # When a custom date range is given, return all runs in that range;
        # otherwise fall back to the fixed limit.
        if not date_from and not date_to:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_run_stats(
        self,
        pipeline_id: uuid.UUID,
        days: int = 30,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        """Compute aggregate stats from run history (bounded by date range or last N days)."""
        cutoff = date_from or (datetime.now(UTC) - timedelta(days=days))
        conditions = [
            PipelineRunHistory.pipeline_id == pipeline_id,
            PipelineRunHistory.duration_seconds.isnot(None),
            PipelineRunHistory.start_date >= cutoff,
        ]
        if date_to:
            conditions.append(PipelineRunHistory.start_date <= date_to)

        stmt = (
            select(
                func.count().label("run_count"),
                func.avg(PipelineRunHistory.duration_seconds).label("avg_duration"),
                func.min(PipelineRunHistory.duration_seconds).label("min_duration"),
                func.max(PipelineRunHistory.duration_seconds).label("max_duration"),
                func.avg(PipelineRunHistory.driver_memory_used_mb).label("avg_driver_mem"),
                func.avg(PipelineRunHistory.executor_memory_peak_mb).label("avg_executor_mem"),
                func.avg(PipelineRunHistory.cpu_utilization_pct).label("avg_cpu"),
                func.avg(
                    case(
                        (PipelineRunHistory.executors_active.isnot(None),
                         PipelineRunHistory.executors_active.cast(Float)),
                        else_=None,
                    )
                ).label("avg_executors"),
                func.sum(
                    case((PipelineRunHistory.status == "success", 1), else_=0)
                ).label("success_count"),
                # sparkMeasure extended metrics
                func.avg(PipelineRunHistory.jvm_gc_time_ms).label("avg_gc_time"),
                func.avg(PipelineRunHistory.shuffle_read_bytes).label("avg_shuffle_read"),
                func.avg(PipelineRunHistory.shuffle_write_bytes).label("avg_shuffle_write"),
                func.avg(PipelineRunHistory.input_bytes).label("avg_input"),
                func.avg(PipelineRunHistory.output_bytes).label("avg_output"),
                func.avg(PipelineRunHistory.memory_bytes_spilled).label("avg_mem_spilled"),
                func.avg(PipelineRunHistory.disk_bytes_spilled).label("avg_disk_spilled"),
                func.avg(PipelineRunHistory.peak_execution_memory).label("avg_peak_exec_mem"),
            )
            .where(*conditions)
        )
        result = await self.session.execute(stmt)
        row = result.one()

        run_count = row.run_count or 0
        success_rate = None
        if run_count > 0:
            success_rate = round((row.success_count / run_count) * 100, 1)

        return {
            "run_count": run_count,
            "avg_duration": round(row.avg_duration, 2) if row.avg_duration else None,
            "min_duration": round(row.min_duration, 2) if row.min_duration else None,
            "max_duration": round(row.max_duration, 2) if row.max_duration else None,
            "success_rate": success_rate,
            "avg_driver_mem_used_mb": round(row.avg_driver_mem) if row.avg_driver_mem else None,
            "avg_executor_mem_peak_mb": round(row.avg_executor_mem) if row.avg_executor_mem else None,
            "avg_cpu_pct": round(row.avg_cpu, 1) if row.avg_cpu else None,
            "avg_executors_active": round(row.avg_executors) if row.avg_executors else None,
            # sparkMeasure extended metrics
            "avg_jvm_gc_time_ms": round(row.avg_gc_time) if row.avg_gc_time else None,
            "avg_shuffle_read_bytes": round(row.avg_shuffle_read) if row.avg_shuffle_read else None,
            "avg_shuffle_write_bytes": round(row.avg_shuffle_write) if row.avg_shuffle_write else None,
            "avg_input_bytes": round(row.avg_input) if row.avg_input else None,
            "avg_output_bytes": round(row.avg_output) if row.avg_output else None,
            "avg_memory_bytes_spilled": round(row.avg_mem_spilled) if row.avg_mem_spilled else None,
            "avg_disk_bytes_spilled": round(row.avg_disk_spilled) if row.avg_disk_spilled else None,
            "avg_peak_execution_memory": round(row.avg_peak_exec_mem) if row.avg_peak_exec_mem else None,
        }

    # --- DAG-level aggregations ---

    async def get_dag_run_stats(
        self,
        dag_id: str,
        days: int = 30,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        """Aggregate run history for all tasks in a DAG (bounded by date range or last N days)."""
        cutoff = date_from or (datetime.now(UTC) - timedelta(days=days))
        conditions = [
            PipelineRunHistory.dag_id == dag_id,
            PipelineRunHistory.duration_seconds.isnot(None),
            PipelineRunHistory.start_date >= cutoff,
        ]
        if date_to:
            conditions.append(PipelineRunHistory.start_date <= date_to)

        stmt = (
            select(
                func.count().label("run_count"),
                func.count(distinct(PipelineRunHistory.dag_run_id)).label("dag_run_count"),
                func.avg(PipelineRunHistory.duration_seconds).label("avg_duration"),
                func.min(PipelineRunHistory.duration_seconds).label("min_duration"),
                func.max(PipelineRunHistory.duration_seconds).label("max_duration"),
                func.sum(
                    case((PipelineRunHistory.status == "success", 1), else_=0)
                ).label("success_count"),
            )
            .where(*conditions)
        )
        result = await self.session.execute(stmt)
        row = result.one()

        run_count = row.run_count or 0
        success_rate = None
        if run_count > 0:
            success_rate = round((row.success_count / run_count) * 100, 1)

        return {
            "run_count": run_count,
            "dag_run_count": row.dag_run_count or 0,
            "avg_duration": round(row.avg_duration, 2) if row.avg_duration else None,
            "min_duration": round(row.min_duration, 2) if row.min_duration else None,
            "max_duration": round(row.max_duration, 2) if row.max_duration else None,
            "success_rate": success_rate,
        }

    async def get_latest_runs_by_dag(self, dag_id: str) -> list[PipelineRunHistory]:
        """Get all task runs for the most recent dag_run_id of a given DAG."""
        # Find latest dag_run_id
        latest_stmt = (
            select(PipelineRunHistory.dag_run_id)
            .where(PipelineRunHistory.dag_id == dag_id)
            .order_by(PipelineRunHistory.start_date.desc().nullslast())
            .limit(1)
        )
        result = await self.session.execute(latest_stmt)
        latest_run_id = result.scalar_one_or_none()
        if not latest_run_id:
            return []

        stmt = (
            select(PipelineRunHistory)
            .where(
                PipelineRunHistory.dag_id == dag_id,
                PipelineRunHistory.dag_run_id == latest_run_id,
            )
            .order_by(PipelineRunHistory.start_date.asc().nullslast())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_typical_finish_hour(
        self,
        dag_id: str,
        days: int = 30,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> str | None:
        """Compute the average finish hour for a DAG from successful runs."""
        cutoff = date_from or (datetime.now(UTC) - timedelta(days=days))
        conditions = [
            PipelineRunHistory.dag_id == dag_id,
            PipelineRunHistory.status == "success",
            PipelineRunHistory.end_date.isnot(None),
            PipelineRunHistory.start_date >= cutoff,
        ]
        if date_to:
            conditions.append(PipelineRunHistory.start_date <= date_to)

        stmt = (
            select(
                func.avg(
                    extract("hour", PipelineRunHistory.end_date)
                    + extract("minute", PipelineRunHistory.end_date) / 60.0
                ).label("avg_hour")
            )
            .where(*conditions)
        )
        result = await self.session.execute(stmt)
        avg_hour = result.scalar_one_or_none()
        if avg_hour is None:
            return None

        hours = int(avg_hour)
        minutes = int((avg_hour - hours) * 60)
        return f"{hours:02d}:{minutes:02d} UTC"
