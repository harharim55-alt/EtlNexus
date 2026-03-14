"""Airflow integration service — polls network DAG task statuses and updates the database."""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.airflow_client import airflow_client, strip_group_prefix
from app.parsers.log_parser import parse_execution_plan, parse_resource_actual
from app.repositories.airflow_repo import AirflowRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.resource_repo import ResourceRepository
from app.repositories.sensor_repo import BouncerRepository

logger = logging.getLogger(__name__)

# Limits concurrent Airflow API calls during poll (mirrors sync semaphore)
_POLL_SEMAPHORE = asyncio.Semaphore(6)

KNOWN_AIRFLOW_STATES = {
    "success", "failed", "upstream_failed", "running", "queued",
    "scheduled", "deferred", "up_for_retry", "up_for_reschedule",
    "skipped", "removed", "restarting", "no_status",
}

# Lower number = higher priority when picking "best" status
_STATUS_PRIORITY = {
    "failed": 0, "upstream_failed": 1, "restarting": 2, "up_for_retry": 3,
    "running": 4, "up_for_reschedule": 5, "queued": 6, "scheduled": 7,
    "deferred": 8, "skipped": 9, "success": 10, "removed": 11,
    "no_status": 12, "unknown": 13,
}


class AirflowService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.airflow_repo = AirflowRepository(session)
        self.pipeline_repo = PipelineRepository(session)
        self.resource_repo = ResourceRepository(session)
        self.bouncer_repo = BouncerRepository(session)

    async def poll_all_statuses(self) -> int:
        """Poll Airflow network DAGs for task-level statuses and update database.

        Uses phased parallel fetching to minimize sequential API calls:
        Phase 1: Parallel fetch dag_runs for all DAGs
        Phase 2: Parallel fetch task_instances for all (dag, run) pairs
        Phase 3: Sequential DB writes + collect log-fetch needs
        Phase 4: Parallel fetch all needed logs
        Phase 5: Sequential DB writes for actuals + status upserts

        Returns the number of pipelines updated.
        """
        pipelines = await self.pipeline_repo.get_all()
        if not pipelines:
            logger.info("No pipelines to poll Airflow for")
            return 0

        all_dags = await airflow_client.get_all_dags()
        if not all_dags:
            logger.warning("Could not fetch DAGs from Airflow")
            return 0

        async def _limited(coro):
            async with _POLL_SEMAPHORE:
                return await coro

        # Build map: task_id → pipeline
        task_to_pipeline = {}
        for pipeline in pipelines:
            if pipeline.task_id:
                task_to_pipeline[pipeline.task_id] = pipeline

        # Build bouncer name set for quick lookup
        all_bouncers = await self.bouncer_repo.get_all()
        bouncer_name_set = {s.sensor_name for s in all_bouncers}
        bouncer_best_status: dict[str, str] = {}

        best: dict[str, dict] = {}
        updated = 0
        history_recorded = 0

        all_dag_ids = [d["dag_id"] for d in all_dags]

        # Phase 1: Parallel fetch dag_runs (5 per DAG)
        runs_results = await asyncio.gather(*[
            _limited(airflow_client.get_dag_runs(did, limit=5))
            for did in all_dag_ids
        ])

        # Phase 2: Collect (dag_id, run, is_latest) and parallel fetch task instances
        run_entries: list[tuple[str, dict, bool]] = []  # (dag_id, run, is_latest)
        for dag_id, runs in zip(all_dag_ids, runs_results):
            if not runs:
                continue
            for i, run in enumerate(runs):
                if run.get("dag_run_id"):
                    run_entries.append((dag_id, run, i == 0))

        instances_results = await asyncio.gather(*[
            _limited(airflow_client.get_task_instances(dag_id, run["dag_run_id"]))
            for dag_id, run, _ in run_entries
        ])

        # Phase 3: Process instances, record history, collect log-fetch needs
        log_fetch_requests: list[tuple[str, str, str, object, str]] = []
        # (dag_id, dag_run_id, airflow_task_id, pipeline, status)

        for (dag_id, run, is_latest), tasks in zip(run_entries, instances_results):
            dag_run_id = run["dag_run_id"]
            exec_date_str = run.get("execution_date")
            exec_date = self._parse_datetime(exec_date_str)

            for task in tasks:
                airflow_task_id = task.get("task_id")
                task_id = strip_group_prefix(airflow_task_id) if airflow_task_id else None

                if task_id in bouncer_name_set and is_latest:
                    state = task.get("state", "unknown")
                    s_status = state if state in KNOWN_AIRFLOW_STATES else "unknown"
                    existing = bouncer_best_status.get(task_id)
                    if existing is None or _STATUS_PRIORITY.get(s_status, 13) < _STATUS_PRIORITY.get(existing, 13):
                        bouncer_best_status[task_id] = s_status
                    continue

                if task_id not in task_to_pipeline:
                    continue

                pipeline = task_to_pipeline[task_id]
                pid = str(pipeline.id)

                state = task.get("state", "unknown")
                status = state if state in KNOWN_AIRFLOW_STATES else "unknown"

                duration = task.get("duration")
                start_date = self._parse_datetime(task.get("start_date"))
                end_date = self._parse_datetime(task.get("end_date"))

                if duration is not None:
                    await self.resource_repo.upsert_run({
                        "pipeline_id": pipeline.id,
                        "dag_id": dag_id,
                        "dag_run_id": dag_run_id,
                        "duration_seconds": duration,
                        "start_date": start_date,
                        "end_date": end_date,
                        "status": status,
                    })
                    history_recorded += 1

                    # Upsert clears actuals on re-run, so always
                    # re-fetch for successful runs
                    if status == "success":
                        needs_actuals = await self.resource_repo.has_null_actuals(
                            pipeline.id, dag_id, dag_run_id
                        )
                        if needs_actuals:
                            log_fetch_requests.append(
                                (dag_id, dag_run_id, airflow_task_id, pipeline, status)
                            )

                if is_latest:
                    if pid in best:
                        existing_date = best[pid].get("execution_date")
                        if (
                            existing_date
                            and exec_date
                            and exec_date <= existing_date
                        ):
                            continue

                    best[pid] = {
                        "pipeline_id": pipeline.id,
                        "dag_id": dag_id,
                        "status": status,
                        "execution_date": exec_date,
                        "last_checked_at": datetime.now(UTC),
                    }

        # Phase 4: Parallel fetch all needed logs
        if log_fetch_requests:
            log_results = await asyncio.gather(*[
                _limited(airflow_client.get_task_log(dag_id, run_id, tid))
                for dag_id, run_id, tid, _, _ in log_fetch_requests
            ])

            for (dag_id, dag_run_id, airflow_task_id, pipeline, _), log_content in zip(
                log_fetch_requests, log_results
            ):
                try:
                    actuals = parse_resource_actual(log_content)
                    plan_json = parse_execution_plan(log_content)
                    if plan_json:
                        actuals = actuals or {}
                        actuals["execution_plan"] = plan_json
                    if actuals:
                        await self.resource_repo.update_run_actuals(
                            pipeline.id, dag_id, dag_run_id, actuals
                        )
                except Exception:
                    logger.debug(
                        "Could not parse resource actuals for %s/%s/%s",
                        dag_id, dag_run_id, airflow_task_id,
                    )

        # Phase 5: Upsert all collected statuses
        for entry in best.values():
            await self.airflow_repo.upsert(entry)
            updated += 1

        bouncer_updated = 0
        for sensor_name, status in bouncer_best_status.items():
            bouncer = await self.bouncer_repo.get_by_name(sensor_name)
            if bouncer:
                bouncer.status = status
                bouncer_updated += 1

        await self.session.commit()
        logger.info(
            "Updated Airflow status for %d pipelines, %d bouncers, recorded %d run history entries",
            updated,
            bouncer_updated,
            history_recorded,
        )
        return updated

    @staticmethod
    def _parse_datetime(date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

