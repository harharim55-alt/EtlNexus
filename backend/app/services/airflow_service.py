"""Airflow integration service — polls network DAG task statuses and updates the database."""

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.airflow_client import airflow_client
from app.repositories.airflow_repo import AirflowRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.resource_repo import ResourceRepository

logger = logging.getLogger(__name__)

TASK_STATE_MAP = {
    "success": "success",
    "failed": "failed",
    "upstream_failed": "failed",
    "running": "running",
    "queued": "running",
    "scheduled": "running",
    "deferred": "running",
    "up_for_retry": "running",
}


class AirflowService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.airflow_repo = AirflowRepository(session)
        self.pipeline_repo = PipelineRepository(session)
        self.resource_repo = ResourceRepository(session)

    async def poll_all_statuses(self) -> int:
        """Poll Airflow network DAGs for task-level statuses and update database.

        Each DAG is a network containing multiple ETL tasks.
        Also records run history (duration + actual resource usage) for statistics.
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

        # Build map: task_id → pipeline (prefer stored task_id, fall back to name conversion)
        task_to_pipeline = {}
        for pipeline in pipelines:
            tid = pipeline.task_id or self._pipeline_to_dag_id(pipeline.name)
            task_to_pipeline[tid] = pipeline

        # Track best status per pipeline (most recent execution wins)
        best: dict[str, dict] = {}
        updated = 0
        history_recorded = 0

        for dag_info in all_dags:
            dag_id = dag_info["dag_id"]

            # Fetch last 5 runs for history (was limit=1)
            runs = await airflow_client.get_dag_runs(dag_id, limit=5)
            if not runs:
                continue

            for run in runs:
                dag_run_id = run.get("dag_run_id")
                if not dag_run_id:
                    continue

                exec_date_str = run.get("execution_date")
                exec_date = self._parse_datetime(exec_date_str)

                # Get task instances for this run
                tasks = await airflow_client.get_task_instances(dag_id, dag_run_id)

                for task in tasks:
                    task_id = task.get("task_id")
                    if task_id not in task_to_pipeline:
                        continue

                    pipeline = task_to_pipeline[task_id]
                    pid = str(pipeline.id)

                    state = task.get("state", "unknown")
                    status = TASK_STATE_MAP.get(state, "unknown")

                    # Strip timezone for DB column
                    clean_exec_date = (
                        exec_date.replace(tzinfo=None) if exec_date else None
                    )

                    # Record run history (duration + actual usage)
                    duration = task.get("duration")
                    start_date = self._parse_datetime(task.get("start_date"))
                    end_date = self._parse_datetime(task.get("end_date"))

                    if duration is not None:
                        is_new = await self.resource_repo.insert_run_if_new({
                            "pipeline_id": pipeline.id,
                            "dag_id": dag_id,
                            "dag_run_id": dag_run_id,
                            "duration_seconds": duration,
                            "start_date": (
                                start_date.replace(tzinfo=None) if start_date else None
                            ),
                            "end_date": (
                                end_date.replace(tzinfo=None) if end_date else None
                            ),
                            "status": status,
                        })

                        if is_new:
                            history_recorded += 1

                        # Parse actual resource usage from logs
                        # For new successful runs, or existing runs missing actuals
                        needs_actuals = False
                        if is_new and status == "success":
                            needs_actuals = True
                        elif not is_new and status == "success":
                            needs_actuals = await self.resource_repo.has_null_actuals(
                                pipeline.id, dag_id, dag_run_id
                            )

                        if needs_actuals:
                            try:
                                log = await airflow_client.get_task_log(
                                    dag_id, dag_run_id, task_id
                                )
                                actuals = self._parse_resource_actual(log)
                                if actuals:
                                    await self.resource_repo.update_run_actuals(
                                        pipeline.id, dag_id, dag_run_id, actuals
                                    )
                            except Exception:
                                logger.debug(
                                    "Could not parse resource actuals for %s/%s/%s",
                                    dag_id, dag_run_id, task_id,
                                )

                    # Track best status (most recent execution wins) — only from latest run
                    if run is runs[0]:
                        if pid in best:
                            existing_date = best[pid].get("execution_date")
                            if (
                                existing_date
                                and clean_exec_date
                                and clean_exec_date <= existing_date
                            ):
                                continue

                        best[pid] = {
                            "pipeline_id": pipeline.id,
                            "dag_id": dag_id,
                            "status": status,
                            "execution_date": clean_exec_date,
                            "last_checked_at": datetime.now(timezone.utc).replace(
                                tzinfo=None
                            ),
                        }

        # Upsert all collected statuses
        for entry in best.values():
            await self.airflow_repo.upsert(entry)
            updated += 1

        await self.session.commit()
        logger.info(
            "Updated Airflow status for %d pipelines, recorded %d run history entries",
            updated,
            history_recorded,
        )
        return updated

    @staticmethod
    def _pipeline_to_dag_id(pipeline_name: str) -> str:
        """Convert pipeline name to expected Airflow task ID.

        E.g., "Shopify Sales Sync" -> "shopify_sales_sync"
        """
        return pipeline_name.lower().replace(" ", "_").replace("-", "_")

    @staticmethod
    def _parse_datetime(date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_resource_actual(log_content: str) -> dict | None:
        """Parse ETL_RESOURCE_ACTUAL JSON from task log."""
        if not log_content:
            return None
        for line in log_content.splitlines():
            if "ETL_RESOURCE_ACTUAL:" in line:
                json_str = line.split("ETL_RESOURCE_ACTUAL:", 1)[1].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        return None
