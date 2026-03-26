"""Resource service — reads allocated configs and run history from DB."""

import json
import logging
import re
import uuid
from datetime import datetime

from app.config import settings
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.resource_repo import ResourceRepository
from app.repositories.resource_stats import ResourceStatsBuilder
from app.schemas.resources import (
    ActualUsage,
    CapacityBar,
    DurationRun,
    ResourceConfigEntry,
    ResourceHistoryRecord,
    ResourceHistoryResponse,
    ResourceMetricsResponse,
)

logger = logging.getLogger(__name__)


class ResourceService:
    def __init__(
        self,
        resource_repo: ResourceRepository,
        pipeline_repo: PipelineRepository,
    ):
        self.resource_repo = resource_repo
        self.pipeline_repo = pipeline_repo
        self.stats = ResourceStatsBuilder(resource_repo.session)

    async def get_resource_metrics(
        self,
        pipeline_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ResourceMetricsResponse | None:
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        # Allocated configs (per DAG)
        configs = await self.resource_repo.get_configs_by_pipeline(pipeline_id)

        # Run history + stats
        runs = await self.resource_repo.get_recent_runs(
            pipeline_id, limit=20, date_from=date_from, date_to=date_to,
        )
        stats = await self.stats.get_run_stats(
            pipeline_id, date_from=date_from, date_to=date_to,
        )

        # Build response
        resource_configs = [
            ResourceConfigEntry(
                dag_id=c.dag_id,
                spark_driver_memory=c.spark_driver_memory,
                spark_executor_memory=c.spark_executor_memory,
                spark_executor_cores=c.spark_executor_cores,
                spark_num_executors=c.spark_num_executors,
                is_dag_override=c.is_dag_override,
            )
            for c in configs
        ]

        recent_runs = [
            DurationRun(
                duration_seconds=r.duration_seconds or 0,
                execution_date=r.start_date.isoformat() if r.start_date else None,
                status=r.status,
                dag_id=r.dag_id,
                spark_application_id=r.spark_application_id,
                metrics_source=r.metrics_source,
            )
            for r in runs
            if r.duration_seconds is not None
        ]

        # Determine dominant metrics source from recent runs
        source_counts: dict[str, int] = {}
        for r in runs:
            if r.metrics_source:
                source_counts[r.metrics_source] = source_counts.get(r.metrics_source, 0) + 1
        dominant_source = max(source_counts, key=source_counts.get) if source_counts else None

        actual_usage = ActualUsage(
            avg_driver_memory_used_mb=stats.get("avg_driver_mem_used_mb"),
            avg_executor_memory_peak_mb=stats.get("avg_executor_mem_peak_mb"),
            avg_cpu_utilization_pct=stats.get("avg_cpu_pct"),
            avg_executors_active=stats.get("avg_executors_active"),
            avg_jvm_gc_time_ms=stats.get("avg_jvm_gc_time_ms"),
            avg_shuffle_read_bytes=stats.get("avg_shuffle_read_bytes"),
            avg_shuffle_write_bytes=stats.get("avg_shuffle_write_bytes"),
            avg_input_bytes=stats.get("avg_input_bytes"),
            avg_output_bytes=stats.get("avg_output_bytes"),
            avg_memory_bytes_spilled=stats.get("avg_memory_bytes_spilled"),
            avg_disk_bytes_spilled=stats.get("avg_disk_bytes_spilled"),
            avg_peak_execution_memory=stats.get("avg_peak_execution_memory"),
            peak_driver_memory_used_mb=stats.get("peak_driver_mem_used_mb"),
            peak_executor_memory_mb=stats.get("peak_executor_mem_mb"),
            peak_cpu_utilization_pct=stats.get("peak_cpu_pct"),
            peak_executors_active=stats.get("peak_executors_active"),
            peak_execution_memory=stats.get("peak_execution_memory"),
            metrics_source=dominant_source,
        )

        # Find latest duration
        latest_duration = None
        if runs:
            for r in runs:
                if r.duration_seconds is not None:
                    latest_duration = r.duration_seconds
                    break

        capacity = self._compute_capacity(configs, actual_usage)

        return ResourceMetricsResponse(
            avg_duration_seconds=stats.get("avg_duration"),
            min_duration_seconds=stats.get("min_duration"),
            max_duration_seconds=stats.get("max_duration"),
            latest_duration_seconds=latest_duration,
            recent_runs=recent_runs,
            run_count=stats.get("run_count", 0),
            success_rate=stats.get("success_rate"),
            resource_configs=resource_configs,
            actual_usage=actual_usage,
            capacity=capacity,
        )

    async def get_resource_history(
        self,
        pipeline_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ResourceHistoryResponse | None:
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        runs, total = await self.stats.get_resource_history(
            pipeline_id, date_from=date_from, date_to=date_to,
        )

        records = [
            ResourceHistoryRecord(
                execution_date=r.start_date.isoformat() if r.start_date else None,
                dag_id=r.dag_id,
                dag_run_id=r.dag_run_id,
                status=r.status,
                duration_seconds=r.duration_seconds,
                driver_memory_used_mb=r.driver_memory_used_mb,
                executor_memory_peak_mb=r.executor_memory_peak_mb,
                cpu_utilization_pct=r.cpu_utilization_pct,
                executors_active=r.executors_active,
                peak_execution_memory=r.peak_execution_memory,
                jvm_gc_time_ms=r.jvm_gc_time_ms,
                shuffle_read_bytes=r.shuffle_read_bytes,
                shuffle_write_bytes=r.shuffle_write_bytes,
                input_bytes=r.input_bytes,
                output_bytes=r.output_bytes,
                memory_bytes_spilled=r.memory_bytes_spilled,
                disk_bytes_spilled=r.disk_bytes_spilled,
                metrics_source=r.metrics_source,
            )
            for r in runs
        ]

        return ResourceHistoryResponse(records=records, total=total)

    async def get_execution_plan(
        self,
        pipeline_id: uuid.UUID,
        dag_run_id: str | None = None,
    ) -> dict | None:
        """Get a specific or latest execution plan for a pipeline."""
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        if dag_run_id:
            run = await self.resource_repo.get_execution_plan_by_run(
                pipeline_id, dag_run_id,
            )
        else:
            run = await self.resource_repo.get_latest_execution_plan(pipeline_id)

        if not run or not run.execution_plan:
            return None

        try:
            plan_data = json.loads(run.execution_plan)
        except (json.JSONDecodeError, TypeError):
            return None

        return {
            "dag_id": run.dag_id,
            "dag_run_id": run.dag_run_id,
            "task_id": pipeline.task_id or pipeline.name,
            "status": run.status,
            "duration_seconds": run.duration_seconds,
            "execution_date": run.start_date.isoformat() if run.start_date else None,
            "execution_plan": plan_data,
        }

    async def get_execution_plan_runs(
        self,
        pipeline_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        """List paginated runs that have execution plans."""
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return {"items": [], "total": 0}
        items, total = await self.resource_repo.get_execution_plan_runs(
            pipeline_id, skip=skip, limit=limit,
        )
        return {"items": items, "total": total}

    def _compute_capacity(
        self,
        configs: list,
        actual_usage: ActualUsage,
    ) -> list[CapacityBar]:
        """Compute capacity bars using the largest allocated config."""
        if not configs:
            return []

        # Find the largest config (prefer non-override, or just the first)
        best = configs[0]
        for c in configs:
            if not c.is_dag_override:
                best = c
                break

        bars: list[CapacityBar] = []

        # Driver Memory — use peak values for capacity
        if best.spark_driver_memory:
            alloc_gb = self._parse_memory_gb(best.spark_driver_memory)
            max_gb = settings.spark_max_driver_memory_gb
            used_gb = (
                actual_usage.peak_driver_memory_used_mb / 1024
                if actual_usage.peak_driver_memory_used_mb
                else 0
            )
            bars.append(
                CapacityBar(
                    label="Driver Memory",
                    allocated=best.spark_driver_memory,
                    used=f"{used_gb:.1f}g" if used_gb else "—",
                    max_capacity=f"{max_gb}g",
                    allocated_pct=round((alloc_gb / max_gb) * 100, 1) if max_gb else 0,
                    used_pct=round((used_gb / max_gb) * 100, 1) if max_gb else 0,
                )
            )

        # Executor Memory — use peak values for capacity
        if best.spark_executor_memory:
            alloc_gb = self._parse_memory_gb(best.spark_executor_memory)
            max_gb = settings.spark_max_executor_memory_gb
            used_gb = (
                actual_usage.peak_executor_memory_mb / 1024
                if actual_usage.peak_executor_memory_mb
                else 0
            )
            bars.append(
                CapacityBar(
                    label="Executor Memory",
                    allocated=best.spark_executor_memory,
                    used=f"{used_gb:.1f}g" if used_gb else "—",
                    max_capacity=f"{max_gb}g",
                    allocated_pct=round((alloc_gb / max_gb) * 100, 1) if max_gb else 0,
                    used_pct=round((used_gb / max_gb) * 100, 1) if max_gb else 0,
                )
            )

        # Executor Cores — use peak CPU for capacity
        if best.spark_executor_cores:
            alloc = best.spark_executor_cores
            max_val = settings.spark_max_executor_cores
            used = (
                round(alloc * (actual_usage.peak_cpu_utilization_pct / 100))
                if actual_usage.peak_cpu_utilization_pct
                else 0
            )
            bars.append(
                CapacityBar(
                    label="CPU Cores",
                    allocated=str(alloc),
                    used=str(used) if used else "—",
                    max_capacity=str(max_val),
                    allocated_pct=round((alloc / max_val) * 100, 1) if max_val else 0,
                    used_pct=round((used / max_val) * 100, 1) if max_val else 0,
                )
            )

        # Num Executors — use peak for capacity
        if best.spark_num_executors:
            alloc = best.spark_num_executors
            max_val = settings.spark_max_total_executors
            used = actual_usage.peak_executors_active or 0
            bars.append(
                CapacityBar(
                    label="Executors",
                    allocated=str(alloc),
                    used=str(used) if used else "—",
                    max_capacity=str(max_val),
                    allocated_pct=round((alloc / max_val) * 100, 1) if max_val else 0,
                    used_pct=round((used / max_val) * 100, 1) if max_val else 0,
                )
            )

        return bars

    @staticmethod
    def _parse_memory_gb(mem_str: str) -> float:
        """Parse memory string to GB. E.g., '8g' -> 8.0, '512m' -> 0.5."""
        match = re.match(r"^(\d+(?:\.\d+)?)\s*([gmtGMT]?)$", mem_str.strip())
        if not match:
            return 0
        val = float(match.group(1))
        unit = match.group(2).lower()
        if unit == "m":
            return val / 1024
        if unit == "t":
            return val * 1024
        return val  # default is GB
