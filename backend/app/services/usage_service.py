import uuid

from app.repositories.airflow_repo import AirflowRepository
from app.repositories.lineage_repo import LineageRepository
from app.repositories.usage_repo import UsageRepository
from app.schemas.usage import PipelineUsageResponse, PipelineUsageSchema


class UsageService:
    def __init__(
        self,
        usage_repo: UsageRepository,
        lineage_repo: LineageRepository,
        airflow_repo: AirflowRepository,
    ):
        self.usage_repo = usage_repo
        self.lineage_repo = lineage_repo
        self.airflow_repo = airflow_repo

    async def get_pipeline_usage(self, pipeline_id: uuid.UUID) -> PipelineUsageResponse:
        # 1. Downstream ETL consumers from lineage + Airflow status
        edges = await self.lineage_repo.get_downstream_pipelines(pipeline_id)
        etl_entries: list[PipelineUsageSchema] = []
        seen: set[uuid.UUID] = set()

        for edge in edges:
            target = edge.target_pipeline
            if not target or target.id in seen:
                continue
            seen.add(target.id)

            dag_id = target.name.lower().replace(" ", "_").replace("-", "_")
            airflow_status = await self.airflow_repo.get_by_pipeline_id(target.id)

            etl_entries.append(PipelineUsageSchema(
                id=str(target.id),
                consumer_name=target.name,
                usage_type="etl",
                description=dag_id,
                last_accessed_at=airflow_status.execution_date if airflow_status else None,
                access_count=0,
                airflow_status=airflow_status.status if airflow_status else "unknown",
            ))

        # 2. Usage entries from PostgreSQL
        db_usages = await self.usage_repo.get_by_pipeline_id(pipeline_id)
        pg_entries = [
            PipelineUsageSchema(
                id=str(u.id),
                consumer_name=u.consumer_name,
                usage_type=u.usage_type,
                description=u.description,
                last_accessed_at=u.last_accessed_at,
                access_count=u.access_count,
            )
            for u in db_usages
        ]

        return PipelineUsageResponse(usages=etl_entries + pg_entries)
