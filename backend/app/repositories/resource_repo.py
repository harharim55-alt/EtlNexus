"""Repository for pipeline resource configs and run history."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import Float, select, func, case
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource_config import PipelineResourceConfig
from app.models.run_history import PipelineRunHistory


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
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
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

    async def insert_run_if_new(self, data: dict) -> bool:
        """Insert a run record if it doesn't already exist. Returns True if inserted."""
        stmt = pg_insert(PipelineRunHistory).values(**data)
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_run_history_pipeline_dag_run"
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
            await self.session.flush()

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
        self, pipeline_id: uuid.UUID, limit: int = 20
    ) -> list[PipelineRunHistory]:
        stmt = (
            select(PipelineRunHistory)
            .where(PipelineRunHistory.pipeline_id == pipeline_id)
            .order_by(PipelineRunHistory.start_date.desc().nullslast())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_run_stats(self, pipeline_id: uuid.UUID, days: int = 30) -> dict:
        """Compute aggregate stats from run history (bounded to last N days)."""
        cutoff = datetime.utcnow() - timedelta(days=days)
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
            )
            .where(
                PipelineRunHistory.pipeline_id == pipeline_id,
                PipelineRunHistory.duration_seconds.isnot(None),
                PipelineRunHistory.start_date >= cutoff,
            )
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
        }
