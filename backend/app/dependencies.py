from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.repositories.airflow_repo import AirflowRepository
from app.repositories.bouncer_repo import BouncerRepository
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.field_frequency_repo import FieldFrequencyRepository
from app.repositories.lineage_repo import LineageRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.resource_repo import ResourceRepository
from app.repositories.revision_repo import RevisionRepository
from app.repositories.team_repo import TeamRepository
from app.repositories.usage_repo import UsageRepository
from app.repositories.user_repo import UserRepository
from app.repositories.visibility_grant_repo import VisibilityGrantRepository
from app.services.ai_service import AIService
from app.services.airflow_sync_service import AirflowSyncService
from app.services.bouncer_service import BouncerService
from app.services.consumer_service import ConsumerService
from app.services.dag_summary_service import DagSummaryService
from app.services.pipeline_service import PipelineService
from app.services.resource_service import ResourceService
from app.services.schema_matrix_service import SchemaMatrixService
from app.services.team_service import TeamService
from app.services.usage_service import UsageService
from app.services.visibility_service import VisibilityService


# Repositories
def get_pipeline_repo(session: AsyncSession = Depends(get_db_session)) -> PipelineRepository:
    return PipelineRepository(session)


def get_lineage_repo(session: AsyncSession = Depends(get_db_session)) -> LineageRepository:
    return LineageRepository(session)


def get_airflow_repo(session: AsyncSession = Depends(get_db_session)) -> AirflowRepository:
    return AirflowRepository(session)


def get_field_frequency_repo(session: AsyncSession = Depends(get_db_session)) -> FieldFrequencyRepository:
    return FieldFrequencyRepository(session)


def get_usage_repo(session: AsyncSession = Depends(get_db_session)) -> UsageRepository:
    return UsageRepository(session)


def get_revision_repo(session: AsyncSession = Depends(get_db_session)) -> RevisionRepository:
    return RevisionRepository(session)


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


def get_dag_task_repo(session: AsyncSession = Depends(get_db_session)) -> DagTaskRepository:
    return DagTaskRepository(session)


def get_usage_service(
    usage_repo: UsageRepository = Depends(get_usage_repo),
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
    dag_task_repo: DagTaskRepository = Depends(get_dag_task_repo),
) -> UsageService:
    return UsageService(usage_repo, pipeline_repo, dag_task_repo)


def get_consumer_service(
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
    dag_task_repo: DagTaskRepository = Depends(get_dag_task_repo),
) -> ConsumerService:
    return ConsumerService(pipeline_repo, dag_task_repo)


def get_resource_repo(session: AsyncSession = Depends(get_db_session)) -> ResourceRepository:
    return ResourceRepository(session)


def get_bouncer_repo(session: AsyncSession = Depends(get_db_session)) -> BouncerRepository:
    return BouncerRepository(session)


def get_user_repo(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    return UserRepository(session)


def get_team_repo(session: AsyncSession = Depends(get_db_session)) -> TeamRepository:
    return TeamRepository(session)


def get_resource_service(
    resource_repo: ResourceRepository = Depends(get_resource_repo),
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
) -> ResourceService:
    return ResourceService(resource_repo, pipeline_repo)


def get_airflow_sync_service(
    session: AsyncSession = Depends(get_db_session),
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
    lineage_repo: LineageRepository = Depends(get_lineage_repo),
    resource_repo: ResourceRepository = Depends(get_resource_repo),
    airflow_repo: AirflowRepository = Depends(get_airflow_repo),
    dag_task_repo: DagTaskRepository = Depends(get_dag_task_repo),
    bouncer_repo: BouncerRepository = Depends(get_bouncer_repo),
    team_repo: TeamRepository = Depends(get_team_repo),
) -> AirflowSyncService:
    return AirflowSyncService(
        session,
        pipeline_repo=pipeline_repo,
        lineage_repo=lineage_repo,
        resource_repo=resource_repo,
        airflow_repo=airflow_repo,
        dag_task_repo=dag_task_repo,
        bouncer_repo=bouncer_repo,
        team_repo=team_repo,
    )


def get_dag_summary_service(
    dag_task_repo: DagTaskRepository = Depends(get_dag_task_repo),
    resource_repo: ResourceRepository = Depends(get_resource_repo),
    airflow_repo: AirflowRepository = Depends(get_airflow_repo),
) -> DagSummaryService:
    return DagSummaryService(dag_task_repo, resource_repo, airflow_repo)


def get_bouncer_service(
    bouncer_repo: BouncerRepository = Depends(get_bouncer_repo),
    dag_task_repo: DagTaskRepository = Depends(get_dag_task_repo),
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
) -> BouncerService:
    return BouncerService(bouncer_repo, dag_task_repo, pipeline_repo)


def get_ai_service(
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
) -> AIService:
    return AIService(pipeline_repo)


def get_visibility_grant_repo(
    session: AsyncSession = Depends(get_db_session),
) -> VisibilityGrantRepository:
    return VisibilityGrantRepository(session)


def get_team_service(
    team_repo: TeamRepository = Depends(get_team_repo),
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
) -> TeamService:
    return TeamService(team_repo, pipeline_repo)


def get_visibility_service(
    grant_repo: VisibilityGrantRepository = Depends(get_visibility_grant_repo),
    team_repo: TeamRepository = Depends(get_team_repo),
) -> VisibilityService:
    return VisibilityService(grant_repo, team_repo)
