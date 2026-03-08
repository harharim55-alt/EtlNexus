"""Usage service — finds downstream consumers from Airflow, enriches with PostgreSQL data."""

import logging

from app.integrations.airflow_client import airflow_client
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.usage_repo import UsageRepository
from app.schemas.usage import PipelineUsageResponse, PipelineUsageSchema
from app.services.airflow_service import TASK_STATE_MAP

logger = logging.getLogger(__name__)


def _to_task_id(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


class UsageService:
    def __init__(self, usage_repo: UsageRepository, pipeline_repo: PipelineRepository):
        self.usage_repo = usage_repo
        self.pipeline_repo = pipeline_repo

    async def get_pipeline_usage(self, etl_name: str) -> PipelineUsageResponse:
        """Find downstream consumers from Airflow and enrich with PostgreSQL usage data.

        Returns the current pipeline as the first entry, followed by downstream consumers.
        """

        # 1. Find all DAGs containing this task
        all_dags = await airflow_client.get_all_dags()
        matching_dag_ids: list[str] = []
        for d in all_dags:
            did = d.get("dag_id", "")
            tasks = await airflow_client.get_dag_tasks(did)
            task_ids = [t["task_id"] for t in tasks]
            if etl_name in task_ids:
                matching_dag_ids.append(did)

        if not matching_dag_ids:
            return PipelineUsageResponse(usages=[])

        # 2. Build pipeline lookup (task_id -> Pipeline)
        all_pipelines = await self.pipeline_repo.get_all()
        task_id_to_pipeline = {_to_task_id(p.name): p for p in all_pipelines}

        # 3. Collect downstream task_ids + status across all DAGs
        downstream_info: dict[str, dict] = {}
        my_status = "unknown"
        my_dag_id = matching_dag_ids[0]

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

            # Track current pipeline's own status
            if etl_name in status_map:
                my_status = status_map[etl_name]
                my_dag_id = dag_id

            for tid in downstream_map.get(etl_name, []):
                if tid not in downstream_info:
                    downstream_info[tid] = {
                        "status": status_map.get(tid, "unknown"),
                        "exec_date": exec_date_str,
                        "dag_id": dag_id,
                    }

        # 4. Load enrichment from PostgreSQL
        enrichment = await self.usage_repo.get_enrichment_map(etl_name)

        # 5. Build downstream consumer entries first (need total reads for current)
        current_pipeline = task_id_to_pipeline.get(etl_name)
        current_category = current_pipeline.category if current_pipeline else ""

        consumer_entries: list[PipelineUsageSchema] = []
        total_reads = 0

        for tid, info in downstream_info.items():
            p = task_id_to_pipeline.get(tid)
            enrich = enrichment.get(tid)
            p_category = p.category if p else ""
            reads = enrich.access_count if enrich else 0
            total_reads += reads

            consumer_entries.append(
                PipelineUsageSchema(
                    id=str(p.id) if p else tid,
                    consumer_name=p.name if p else tid.replace("_", " ").title(),
                    usage_type="api" if p_category == "API" else "etl",
                    description=enrich.description if enrich else None,
                    last_accessed_at=enrich.last_accessed_at if enrich else None,
                    access_count=reads,
                    airflow_status=info["status"],
                    dag_id=info["dag_id"],
                    is_current=False,
                )
            )

        # Current pipeline first, then downstream consumers
        usages: list[PipelineUsageSchema] = [
            PipelineUsageSchema(
                id=str(current_pipeline.id) if current_pipeline else etl_name,
                consumer_name=current_pipeline.name if current_pipeline else etl_name.replace("_", " ").title(),
                usage_type="api" if current_category == "API" else "etl",
                description=current_pipeline.description if current_pipeline else None,
                last_accessed_at=None,
                access_count=total_reads,
                airflow_status=my_status,
                dag_id=my_dag_id,
                is_current=True,
            ),
            *consumer_entries,
        ]

        return PipelineUsageResponse(usages=usages)
