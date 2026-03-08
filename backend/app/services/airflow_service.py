"""Airflow integration service — polls network DAG task statuses and updates the database."""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.airflow_client import airflow_client
from app.repositories.airflow_repo import AirflowRepository
from app.repositories.pipeline_repo import PipelineRepository

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

    async def poll_all_statuses(self) -> int:
        """Poll Airflow network DAGs for task-level statuses and update database.

        Each DAG is a network containing multiple ETL tasks.
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

        # Build map: task_id (snake_case pipeline name) → pipeline
        task_to_pipeline = {}
        for pipeline in pipelines:
            task_id = self._pipeline_to_dag_id(pipeline.name)
            task_to_pipeline[task_id] = pipeline

        # Track best status per pipeline (most recent execution wins)
        best: dict[str, dict] = {}
        updated = 0

        for dag_info in all_dags:
            dag_id = dag_info["dag_id"]

            # Get latest run for this network DAG
            runs = await airflow_client.get_dag_runs(dag_id, limit=1)
            if not runs:
                continue

            run = runs[0]
            dag_run_id = run.get("dag_run_id")
            if not dag_run_id:
                continue

            exec_date_str = run.get("execution_date")
            exec_date = None
            if exec_date_str:
                try:
                    exec_date = datetime.fromisoformat(
                        exec_date_str.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

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
                clean_exec_date = exec_date.replace(tzinfo=None) if exec_date else None

                # Keep the most recent execution if pipeline appears in multiple DAGs
                if pid in best:
                    existing_date = best[pid].get("execution_date")
                    if existing_date and clean_exec_date and clean_exec_date <= existing_date:
                        continue

                best[pid] = {
                    "pipeline_id": pipeline.id,
                    "dag_id": dag_id,
                    "status": status,
                    "execution_date": clean_exec_date,
                    "last_checked_at": datetime.now(timezone.utc).replace(tzinfo=None),
                }

        # Upsert all collected statuses
        for entry in best.values():
            await self.airflow_repo.upsert(entry)
            updated += 1

        await self.session.commit()
        logger.info("Updated Airflow status for %d pipelines", updated)
        return updated

    @staticmethod
    def _pipeline_to_dag_id(pipeline_name: str) -> str:
        """Convert pipeline name to expected Airflow task ID.

        E.g., "Shopify Sales Sync" -> "shopify_sales_sync"
        """
        return pipeline_name.lower().replace(" ", "_").replace("-", "_")
