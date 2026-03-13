"""Consumer service — finds downstream pipelines from cached DAG task data."""

import logging
import re

from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.schemas.consumer import PipelineConsumersResponse, PipelineConsumerSchema

logger = logging.getLogger(__name__)


class ConsumerService:
    def __init__(self, pipeline_repo: PipelineRepository, dag_task_repo: DagTaskRepository):
        self.pipeline_repo = pipeline_repo
        self.dag_task_repo = dag_task_repo

    async def get_pipeline_consumers(self, etl_name: str) -> PipelineConsumersResponse:
        """Find downstream pipelines that consume this ETL's output, with status from DB."""

        # Get all DAG entries for this task
        dag_entries = await self.dag_task_repo.get_dags_for_task(etl_name)
        if not dag_entries:
            return PipelineConsumersResponse(consumers=[])

        # Build pipeline lookup by task_id (PascalCase)
        all_pipelines = await self.pipeline_repo.get_all()
        task_id_to_pipeline = {p.task_id: p for p in all_pipelines if p.task_id}

        # Collect downstream tasks across all DAGs (deduplicated by task_id)
        downstream_info: dict[str, dict] = {}
        for entry in dag_entries:
            for tid in entry.downstream_task_ids or []:
                if tid not in downstream_info:
                    p = task_id_to_pipeline.get(tid)
                    status = "unknown"
                    if p and p.airflow_status:
                        status = p.airflow_status.status
                    exec_date = None
                    if p and p.airflow_status and p.airflow_status.execution_date:
                        exec_date = p.airflow_status.execution_date.isoformat()
                    downstream_info[tid] = {
                        "status": status,
                        "exec_date": exec_date,
                        "dag_id": entry.dag_id,
                    }

        # Build response
        consumers: list[PipelineConsumerSchema] = []
        for tid, info in downstream_info.items():
            p = task_id_to_pipeline.get(tid)
            consumers.append(
                PipelineConsumerSchema(
                    pipeline_id=str(p.id) if p else tid,
                    pipeline_name=p.name if p else re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", tid).replace("_", " ").strip().title(),
                    dag_id=info["dag_id"],
                    airflow_status=info["status"],
                    last_run_at=info["exec_date"],
                )
            )

        return PipelineConsumersResponse(consumers=consumers)
