"""Consumer service — finds downstream pipelines via lineage and enriches with Airflow status."""

import uuid

from app.repositories.airflow_repo import AirflowRepository
from app.repositories.lineage_repo import LineageRepository
from app.schemas.consumer import PipelineConsumersResponse, PipelineConsumerSchema


class ConsumerService:
    def __init__(self, lineage_repo: LineageRepository, airflow_repo: AirflowRepository):
        self.lineage_repo = lineage_repo
        self.airflow_repo = airflow_repo

    async def get_pipeline_consumers(self, pipeline_id: uuid.UUID) -> PipelineConsumersResponse:
        """Find downstream pipelines that consume this pipeline's output, with Airflow status."""
        edges = await self.lineage_repo.get_downstream_pipelines(pipeline_id)

        consumers: list[PipelineConsumerSchema] = []
        seen: set[uuid.UUID] = set()

        for edge in edges:
            target = edge.target_pipeline
            if not target or target.id in seen:
                continue
            seen.add(target.id)

            dag_id = self._pipeline_to_dag_id(target.name)
            airflow_status = await self.airflow_repo.get_by_pipeline_id(target.id)

            consumers.append(PipelineConsumerSchema(
                pipeline_id=str(target.id),
                pipeline_name=target.name,
                dag_id=dag_id,
                airflow_status=airflow_status.status if airflow_status else "unknown",
                last_run_at=airflow_status.execution_date if airflow_status else None,
            ))

        return PipelineConsumersResponse(consumers=consumers)

    @staticmethod
    def _pipeline_to_dag_id(pipeline_name: str) -> str:
        return pipeline_name.lower().replace(" ", "_").replace("-", "_")
