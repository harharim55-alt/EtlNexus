"""Usage service — finds downstream consumers from cached DAG data, enriches with oasis_prod metrics."""

import logging
import re
from datetime import datetime

from app.integrations.oasis_prod_client import oasis_prod_client
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.schemas.usage import PipelineUsageResponse, PipelineUsageSchema

logger = logging.getLogger(__name__)


class UsageService:
    def __init__(
        self,
        pipeline_repo: PipelineRepository,
        dag_task_repo: DagTaskRepository,
    ):
        self.pipeline_repo = pipeline_repo
        self.dag_task_repo = dag_task_repo

    async def get_pipeline_usage(
        self,
        etl_name: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        network: str | None = None,
    ) -> PipelineUsageResponse:
        """Find downstream consumers from DAG topology and enrich with oasis_prod read metrics."""

        # 1. Find all DAGs containing this task
        dag_entries = await self.dag_task_repo.get_dags_for_task(etl_name)
        if not dag_entries:
            return PipelineUsageResponse(usages=[])

        # 2. Build pipeline lookup by task_id
        task_id_to_pipeline = await self.pipeline_repo.get_task_id_map()

        # 3. Collect downstream task_ids + status across all DAGs
        downstream_info: dict[str, dict] = {}
        my_status = "unknown"
        my_dag_id = dag_entries[0].dag_id

        current_pipeline = task_id_to_pipeline.get(etl_name)
        if current_pipeline:
            my_status = current_pipeline.status

        for entry in dag_entries:
            for tid in entry.downstream_task_ids or []:
                if tid not in downstream_info:
                    p = task_id_to_pipeline.get(tid)
                    status = p.status if p else "unknown"
                    downstream_info[tid] = {
                        "status": status,
                        "dag_id": entry.dag_id,
                    }

        # 3a. Apply network filter to downstream consumers
        if network:
            downstream_info = {
                tid: info for tid, info in downstream_info.items()
                if info["dag_id"] == network
            }

        # 4. Fetch live metrics from oasis_prod — current pipeline (detailed) + downstream (batch)
        own_unique_reads = 0
        own_total_reads = 0
        own_last_accessed = None

        current_team = (current_pipeline.team or "").lower() if current_pipeline else ""
        if current_team:
            metrics = await oasis_prod_client.get_usage_metrics(
                data_source_name=current_team,
                data_name=etl_name,
                date_from=date_from,
                date_to=date_to,
            )
            if metrics:
                own_unique_reads = metrics.unique_reads
                own_total_reads = metrics.total_reads
                if metrics.consumers:
                    own_last_accessed = metrics.consumers[0].last_accessed_at

        # 4a. Batch fetch metrics for all downstream consumers in a single query
        downstream_products: list[tuple[str, str]] = []
        for tid in downstream_info:
            p = task_id_to_pipeline.get(tid)
            if p and p.team:
                downstream_products.append((p.team.lower(), tid))

        batch_metrics = await oasis_prod_client.get_batch_usage_metrics(
            downstream_products, date_from=date_from, date_to=date_to,
        )

        # 5. Build downstream consumer entries
        current_category = current_pipeline.category if current_pipeline else ""

        consumer_entries: list[PipelineUsageSchema] = []
        for tid, info in downstream_info.items():
            p = task_id_to_pipeline.get(tid)
            p_category = p.category if p else ""
            p_team = (p.team or "").lower() if p else ""

            batch_key = f"{p_team}.{tid}" if p_team else ""
            m = batch_metrics.get(batch_key)

            consumer_entries.append(
                PipelineUsageSchema(
                    id=str(p.id) if p else tid,
                    consumer_name=p.name if p else re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", tid).replace("_", " ").strip().title(),
                    usage_type="api" if "api" in p_category.lower() else "etl",
                    description=None,
                    last_accessed_at=None,
                    unique_reads=m.unique_reads if m else 0,
                    total_reads=m.total_reads if m else 0,
                    airflow_status=info["status"],
                    dag_id=info["dag_id"],
                    is_current=False,
                )
            )

        # 6. Current pipeline first, then downstream consumers
        usages: list[PipelineUsageSchema] = [
            PipelineUsageSchema(
                id=str(current_pipeline.id) if current_pipeline else etl_name,
                consumer_name=current_pipeline.name if current_pipeline else re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", etl_name).replace("_", " ").strip().title(),
                usage_type="api" if "api" in current_category.lower() else "etl",
                description=current_pipeline.description if current_pipeline else None,
                last_accessed_at=own_last_accessed,
                unique_reads=own_unique_reads,
                total_reads=own_total_reads,
                airflow_status=my_status,
                dag_id=my_dag_id,
                is_current=True,
            ),
            *consumer_entries,
        ]

        return PipelineUsageResponse(usages=usages)
