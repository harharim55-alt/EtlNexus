"""Aggregation and statistics builder for pipeline run history."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Float, case, distinct, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run_history import PipelineRunHistory


class ResourceStatsBuilder:
    def __init__(self, session: AsyncSession):
        self.session = session

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
                # Peak (max) values for capacity bars
                func.max(PipelineRunHistory.driver_memory_used_mb).label("peak_driver_mem"),
                func.max(PipelineRunHistory.executor_memory_peak_mb).label("peak_executor_mem"),
                func.max(PipelineRunHistory.cpu_utilization_pct).label("peak_cpu"),
                func.max(
                    case(
                        (PipelineRunHistory.executors_active.isnot(None),
                         PipelineRunHistory.executors_active.cast(Float)),
                        else_=None,
                    )
                ).label("peak_executors"),
                func.max(PipelineRunHistory.peak_execution_memory).label("peak_exec_mem"),
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
            # Peak (max) values for capacity bars
            "peak_driver_mem_used_mb": round(row.peak_driver_mem) if row.peak_driver_mem else None,
            "peak_executor_mem_mb": round(row.peak_executor_mem) if row.peak_executor_mem else None,
            "peak_cpu_pct": round(row.peak_cpu, 1) if row.peak_cpu else None,
            "peak_executors_active": round(row.peak_executors) if row.peak_executors else None,
            "peak_execution_memory": round(row.peak_exec_mem) if row.peak_exec_mem else None,
        }

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

    async def get_resource_history(
        self,
        pipeline_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[PipelineRunHistory], int]:
        """Get per-run resource records for time-series charting (chronological order)."""
        cutoff = date_from or (datetime.now(UTC) - timedelta(days=30))
        conditions = [
            PipelineRunHistory.pipeline_id == pipeline_id,
            PipelineRunHistory.duration_seconds.isnot(None),
            PipelineRunHistory.start_date >= cutoff,
        ]
        if date_to:
            conditions.append(PipelineRunHistory.start_date <= date_to)

        count_stmt = (
            select(func.count())
            .select_from(PipelineRunHistory)
            .where(*conditions)
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            select(PipelineRunHistory)
            .where(*conditions)
            .order_by(PipelineRunHistory.start_date.asc().nullslast())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
