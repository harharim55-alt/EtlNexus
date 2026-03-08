"""Airflow integration service — polls DAG statuses and updates the database."""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.airflow_client import airflow_client
from app.repositories.airflow_repo import AirflowRepository
from app.repositories.pipeline_repo import PipelineRepository

logger = logging.getLogger(__name__)


class AirflowService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.airflow_repo = AirflowRepository(session)
        self.pipeline_repo = PipelineRepository(session)

    async def poll_all_statuses(self) -> int:
        """Poll Airflow for latest DAG run statuses and update database.

        Returns the number of pipelines updated.
        """
        pipelines = await self.pipeline_repo.get_all()
        if not pipelines:
            logger.info("No pipelines to poll Airflow for")
            return 0

        # Get all DAGs from Airflow
        all_dags = await airflow_client.get_all_dags()
        if not all_dags:
            logger.warning("Could not fetch DAGs from Airflow — marking all as unknown")
            return 0

        dag_ids = {dag["dag_id"] for dag in all_dags}
        updated = 0

        for pipeline in pipelines:
            # Convention: DAG ID matches pipeline name (snake_case)
            dag_id = self._pipeline_to_dag_id(pipeline.name)
            if dag_id not in dag_ids:
                continue

            run_info = await airflow_client.get_latest_dag_run_status(dag_id)
            # Strip timezone info — DB column is TIMESTAMP WITHOUT TIME ZONE
            exec_date = run_info["execution_date"]
            if exec_date and hasattr(exec_date, "replace"):
                exec_date = exec_date.replace(tzinfo=None)
            await self.airflow_repo.upsert({
                "pipeline_id": pipeline.id,
                "dag_id": dag_id,
                "status": run_info["status"],
                "execution_date": exec_date,
                "last_checked_at": datetime.now(timezone.utc).replace(tzinfo=None),
            })
            updated += 1

        await self.session.commit()
        logger.info("Updated Airflow status for %d pipelines", updated)
        return updated

    @staticmethod
    def _pipeline_to_dag_id(pipeline_name: str) -> str:
        """Convert pipeline name to expected Airflow DAG ID.

        E.g., "Shopify Sales Sync" -> "shopify_sales_sync"
        """
        return pipeline_name.lower().replace(" ", "_").replace("-", "_")
