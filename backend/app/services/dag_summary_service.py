"""Service for DAG-level summary statistics."""

import logging

from app.cache import dag_summary_cache
from app.integrations.airflow_client import airflow_client
from app.repositories.airflow_repo import AirflowRepository
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.resource_repo import ResourceRepository
from app.schemas.dag_summary import (
    DagSummary,
    DagSummaryAggregate,
    DagSummaryResponse,
    DagTaskSummary,
)

logger = logging.getLogger(__name__)

CACHE_KEY = "dag_summary"


class DagSummaryService:
    def __init__(
        self,
        dag_task_repo: DagTaskRepository,
        resource_repo: ResourceRepository,
        airflow_repo: AirflowRepository,
    ):
        self.dag_task_repo = dag_task_repo
        self.resource_repo = resource_repo
        self.airflow_repo = airflow_repo

    async def get_dag_summaries(self) -> DagSummaryResponse:
        cached = dag_summary_cache.get(CACHE_KEY)
        if cached is not None:
            return cached

        result = await self._build_dag_summaries()
        dag_summary_cache.set(CACHE_KEY, result)
        return result

    async def _build_dag_summaries(self) -> DagSummaryResponse:
        # Batch fetch all required data
        all_dag_ids = await self.dag_task_repo.get_all_dag_ids()
        task_counts = await self.dag_task_repo.count_tasks_per_dag()
        pipeline_counts = await self.dag_task_repo.count_pipelines_per_dag()

        # Airflow metadata (cached 5min by airflow_client)
        airflow_dags = await airflow_client.get_all_dags()
        dag_info_map = {d["dag_id"]: d for d in airflow_dags}

        # Airflow statuses for per-task status lookup
        all_statuses = await self.airflow_repo.get_all()
        status_by_pipeline = {str(s.pipeline_id): s for s in all_statuses}

        dags: list[DagSummary] = []
        total_pipelines = 0
        total_runs_30d = 0
        all_success = 0
        all_total = 0
        active_dags = 0

        for dag_id in all_dag_ids:
            dag_info = dag_info_map.get(dag_id, {})
            is_paused = dag_info.get("is_paused", False)
            if not is_paused:
                active_dags += 1

            tc = task_counts.get(dag_id, 0)
            pc = pipeline_counts.get(dag_id, 0)
            total_pipelines += pc

            # Run stats (30d)
            run_stats = await self.resource_repo.get_dag_run_stats(dag_id)
            total_runs_30d += run_stats["dag_run_count"]

            # Latest run tasks
            latest_runs = await self.resource_repo.get_latest_runs_by_dag(dag_id)

            # Typical finish hour
            finish_hour = await self.resource_repo.get_typical_finish_hour(dag_id)

            # Tasks in this DAG (eager-load pipeline for name lookup)
            tasks_in_dag = await self.dag_task_repo.get_tasks_for_dag_with_pipeline(dag_id)

            # Build per-task summaries
            task_summaries: list[DagTaskSummary] = []
            success_count = 0
            failed_count = 0
            upstream_failed_count = 0
            running_count = 0
            queued_count = 0
            unknown_count = 0

            # Map latest run durations by pipeline_id
            latest_dur_by_pipeline: dict[str, float] = {}
            for run in latest_runs:
                if run.pipeline_id and run.duration_seconds is not None:
                    latest_dur_by_pipeline[str(run.pipeline_id)] = run.duration_seconds

            for task in tasks_in_dag:
                pid_str = str(task.pipeline_id) if task.pipeline_id else None
                status_obj = status_by_pipeline.get(pid_str) if pid_str else None
                task_status = status_obj.status if status_obj else "unknown"

                if task_status == "success":
                    success_count += 1
                elif task_status == "failed":
                    failed_count += 1
                elif task_status == "upstream_failed":
                    upstream_failed_count += 1
                elif task_status == "running":
                    running_count += 1
                elif task_status == "queued":
                    queued_count += 1
                else:
                    unknown_count += 1

                pipeline_name = None
                if task.pipeline:
                    pipeline_name = task.pipeline.name

                task_summaries.append(DagTaskSummary(
                    task_id=task.task_id,
                    pipeline_name=pipeline_name,
                    pipeline_id=pid_str,
                    status=task_status,
                    latest_duration_seconds=latest_dur_by_pipeline.get(pid_str) if pid_str else None,
                    avg_duration_seconds=run_stats["avg_duration"],
                    task_group_id=task.task_group_id,
                ))

            all_success += success_count
            all_total += tc

            sr = None
            if tc > 0:
                sr = round((success_count / tc) * 100, 1)

            # Latest run timing
            latest_start = None
            latest_end = None
            total_dur = None
            avg_dur = None
            min_dur = None
            max_dur = None

            if latest_runs:
                starts = [r.start_date for r in latest_runs if r.start_date]
                ends = [r.end_date for r in latest_runs if r.end_date]
                durs = [r.duration_seconds for r in latest_runs if r.duration_seconds is not None]

                if starts:
                    latest_start = min(starts).isoformat()
                if ends:
                    latest_end = max(ends).isoformat()
                if durs:
                    total_dur = round(sum(durs), 2)
                    avg_dur = round(sum(durs) / len(durs), 2)
                    min_dur = round(min(durs), 2)
                    max_dur = round(max(durs), 2)

            # Schedule interval formatting
            schedule = dag_info.get("schedule_interval")
            if isinstance(schedule, dict):
                schedule = schedule.get("value", str(schedule))

            dags.append(DagSummary(
                dag_id=dag_id,
                description=dag_info.get("description"),
                schedule_interval=str(schedule) if schedule else None,
                is_paused=is_paused,
                task_count=tc,
                pipeline_count=pc,
                total_duration_seconds=total_dur,
                avg_task_duration_seconds=avg_dur,
                min_task_duration_seconds=min_dur,
                max_task_duration_seconds=max_dur,
                success_count=success_count,
                failed_count=failed_count,
                upstream_failed_count=upstream_failed_count,
                running_count=running_count,
                queued_count=queued_count,
                unknown_count=unknown_count,
                success_rate=sr,
                latest_run_start=latest_start,
                latest_run_end=latest_end,
                typical_finish_hour=finish_hour,
                total_runs_30d=run_stats["dag_run_count"],
                dag_success_rate_30d=run_stats["success_rate"],
                tasks=task_summaries,
            ))

        overall_sr = None
        if all_total > 0:
            overall_sr = round((all_success / all_total) * 100, 1)

        aggregate = DagSummaryAggregate(
            total_dags=len(all_dag_ids),
            total_pipelines=total_pipelines,
            active_dags=active_dags,
            overall_success_rate=overall_sr,
            total_runs_30d=total_runs_30d,
        )

        return DagSummaryResponse(aggregate=aggregate, dags=dags)
