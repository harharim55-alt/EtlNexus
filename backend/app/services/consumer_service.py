"""Consumer service — finds downstream pipelines from Airflow with status."""

import logging

from app.integrations.airflow_client import airflow_client
from app.repositories.pipeline_repo import PipelineRepository
from app.schemas.consumer import PipelineConsumersResponse, PipelineConsumerSchema
from app.services.airflow_service import TASK_STATE_MAP

logger = logging.getLogger(__name__)


def _to_task_id(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


class ConsumerService:
    def __init__(self, pipeline_repo: PipelineRepository):
        self.pipeline_repo = pipeline_repo

    async def get_pipeline_consumers(self, etl_name: str) -> PipelineConsumersResponse:
        """Find downstream pipelines that consume this ETL's output, with Airflow status."""

        # Find all DAGs containing this task
        all_dags = await airflow_client.get_all_dags()
        matching_dag_ids: list[str] = []
        for d in all_dags:
            did = d.get("dag_id", "")
            tasks = await airflow_client.get_dag_tasks(did)
            task_ids = [t["task_id"] for t in tasks]
            if etl_name in task_ids:
                matching_dag_ids.append(did)

        if not matching_dag_ids:
            return PipelineConsumersResponse(consumers=[])

        # Build pipeline lookup
        all_pipelines = await self.pipeline_repo.get_all()
        task_id_to_pipeline = {_to_task_id(p.name): p for p in all_pipelines}

        # Collect downstream tasks + status
        downstream_info: dict[str, dict] = {}
        for dag_id in matching_dag_ids:
            tasks_def = await airflow_client.get_dag_tasks(dag_id)
            downstream_map = {
                t["task_id"]: t.get("downstream_task_ids", []) for t in tasks_def
            }

            status_map: dict[str, str] = {}
            exec_date_str = None
            runs = await airflow_client.get_dag_runs(dag_id, limit=1)
            if runs:
                run = runs[0]
                dag_run_id = run.get("dag_run_id")
                exec_date_str = run.get("execution_date")
                if dag_run_id:
                    instances = await airflow_client.get_task_instances(
                        dag_id, dag_run_id
                    )
                    for inst in instances:
                        tid = inst["task_id"]
                        raw_state = inst.get("state", "unknown")
                        status_map[tid] = TASK_STATE_MAP.get(raw_state, "unknown")

            for tid in downstream_map.get(etl_name, []):
                if tid not in downstream_info:
                    downstream_info[tid] = {
                        "status": status_map.get(tid, "unknown"),
                        "exec_date": exec_date_str,
                        "dag_id": dag_id,
                    }

        # Build response
        consumers: list[PipelineConsumerSchema] = []
        for tid, info in downstream_info.items():
            p = task_id_to_pipeline.get(tid)
            consumers.append(
                PipelineConsumerSchema(
                    pipeline_id=str(p.id) if p else tid,
                    pipeline_name=p.name if p else tid.replace("_", " ").title(),
                    dag_id=info["dag_id"],
                    airflow_status=info["status"],
                    last_run_at=info["exec_date"],
                )
            )

        return PipelineConsumersResponse(consumers=consumers)
