from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.repositories.airflow_repo import AirflowRepository
from app.repositories.dag_network_repo import DagNetworkRepository
from app.repositories.field_frequency_repo import FieldFrequencyRepository
from app.repositories.lineage_repo import LineageRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.services.ai_service import AIService
from app.services.pipeline_service import PipelineService
from app.services.schema_matrix_service import SchemaMatrixService


# Repositories
def get_pipeline_repo(session: AsyncSession = Depends(get_db_session)) -> PipelineRepository:
    return PipelineRepository(session)


def get_lineage_repo(session: AsyncSession = Depends(get_db_session)) -> LineageRepository:
    return LineageRepository(session)


def get_airflow_repo(session: AsyncSession = Depends(get_db_session)) -> AirflowRepository:
    return AirflowRepository(session)


def get_dag_network_repo(session: AsyncSession = Depends(get_db_session)) -> DagNetworkRepository:
    return DagNetworkRepository(session)


def get_field_frequency_repo(session: AsyncSession = Depends(get_db_session)) -> FieldFrequencyRepository:
    return FieldFrequencyRepository(session)


# Services
def get_pipeline_service(
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
    lineage_repo: LineageRepository = Depends(get_lineage_repo),
) -> PipelineService:
    return PipelineService(pipeline_repo, lineage_repo)


def get_schema_matrix_service(
    field_freq_repo: FieldFrequencyRepository = Depends(get_field_frequency_repo),
) -> SchemaMatrixService:
    return SchemaMatrixService(field_freq_repo)


def get_ai_service(
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
) -> AIService:
    return AIService(pipeline_repo)
