"""Usage service — finds downstream consumers from cached DAG data, enriches with PostgreSQL data."""

import logging

from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.usage_repo import UsageRepository
from app.schemas.usage import PipelineUsageResponse, PipelineUsageSchema

logger = logging.getLogger(__name__)


def _to_task_id(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


class UsageService:
    def __init__(
        self,
        usage_repo: UsageRepository,
        pipeline_repo: PipelineRepository,
        dag_task_repo: DagTaskRepository,
    ):
        self.usage_repo = usage_repo
        self.pipeline_repo = pipeline_repo
        self.dag_task_repo = dag_task_repo

    async def get_pipeline_usage(self, etl_name: str) -> PipelineUsageResponse:
        """Find downstream consumers from cached DAG data and enrich with PostgreSQL usage data.

        Returns the current pipeline as the first entry, followed by downstream consumers.
        """

        # 1. Find all DAGs containing this task (from DB)
        dag_entries = await self.dag_task_repo.get_dags_for_task(etl_name)
        if not dag_entries:
            return PipelineUsageResponse(usages=[])

        # 2. Build pipeline lookup (task_id -> Pipeline)
        all_pipelines = await self.pipeline_repo.get_all()
        task_id_to_pipeline = {_to_task_id(p.name): p for p in all_pipelines}

        # 3. Collect downstream task_ids + status across all DAGs
        downstream_info: dict[str, dict] = {}
        my_status = "unknown"
        my_dag_id = dag_entries[0].dag_id

        current_pipeline = task_id_to_pipeline.get(etl_name)
        if current_pipeline and current_pipeline.airflow_status:
            my_status = current_pipeline.airflow_status.status

        for entry in dag_entries:
            for tid in entry.downstream_task_ids or []:
                if tid not in downstream_info:
                    p = task_id_to_pipeline.get(tid)
                    status = "unknown"
                    exec_date = None
                    if p and p.airflow_status:
                        status = p.airflow_status.status
                        if p.airflow_status.execution_date:
                            exec_date = p.airflow_status.execution_date.isoformat()
                    downstream_info[tid] = {
                        "status": status,
                        "exec_date": exec_date,
                        "dag_id": entry.dag_id,
                    }

        # 4. Load enrichment from PostgreSQL
        enrichment = await self.usage_repo.get_enrichment_map(etl_name)

        # 5. Build downstream consumer entries
        current_category = current_pipeline.category if current_pipeline else ""

        consumer_entries: list[PipelineUsageSchema] = []

        for tid, info in downstream_info.items():
            p = task_id_to_pipeline.get(tid)
            enrich = enrichment.get(tid)
            p_category = p.category if p else ""
            reads = enrich.access_count if enrich else 0

            consumer_entries.append(
                PipelineUsageSchema(
                    id=str(p.id) if p else tid,
                    consumer_name=p.name if p else tid.replace("_", " ").title(),
                    usage_type="api" if "api" in p_category.lower() else "etl",
                    description=enrich.description if enrich else None,
                    last_accessed_at=enrich.last_accessed_at if enrich else None,
                    access_count=reads,
                    airflow_status=info["status"],
                    dag_id=info["dag_id"],
                    is_current=False,
                )
            )

        # Current ETL's own reads from self-entry in pipeline_usages
        self_entry = enrichment.get(etl_name)
        own_reads = self_entry.access_count if self_entry else 0

        # Current pipeline first, then downstream consumers
        usages: list[PipelineUsageSchema] = [
            PipelineUsageSchema(
                id=str(current_pipeline.id) if current_pipeline else etl_name,
                consumer_name=current_pipeline.name if current_pipeline else etl_name.replace("_", " ").title(),
                usage_type="api" if "api" in current_category.lower() else "etl",
                description=current_pipeline.description if current_pipeline else None,
                last_accessed_at=self_entry.last_accessed_at if self_entry else None,
                access_count=own_reads,
                airflow_status=my_status,
                dag_id=my_dag_id,
                is_current=True,
            ),
            *consumer_entries,
        ]

        return PipelineUsageResponse(usages=usages)
