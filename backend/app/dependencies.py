from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db_session
from app.models.user import User
from app.repositories.field_frequency_repo import FieldFrequencyRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.revision_repo import RevisionRepository
from app.repositories.tag_repo import TagRepository
from app.repositories.team_repo import TeamRepository
from app.repositories.user_repo import UserRepository
from app.repositories.visibility_grant_repo import VisibilityGrantRepository
from app.services.ai_service import AIService
from app.services.pipeline_service import PipelineService
from app.services.schema_matrix_service import SchemaMatrixService
from app.services.tag_service import TagService
from app.services.team_service import TeamService
from app.services.visibility_service import VisibilityService


# Repositories
def get_pipeline_repo(session: AsyncSession = Depends(get_db_session)) -> PipelineRepository:
    return PipelineRepository(session)


def get_field_frequency_repo(session: AsyncSession = Depends(get_db_session)) -> FieldFrequencyRepository:
    return FieldFrequencyRepository(session)


def get_revision_repo(session: AsyncSession = Depends(get_db_session)) -> RevisionRepository:
    return RevisionRepository(session)


def get_user_repo(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    return UserRepository(session)


def get_team_repo(session: AsyncSession = Depends(get_db_session)) -> TeamRepository:
    return TeamRepository(session)


def get_visibility_grant_repo(
    session: AsyncSession = Depends(get_db_session),
) -> VisibilityGrantRepository:
    return VisibilityGrantRepository(session)


def get_tag_repo(session: AsyncSession = Depends(get_db_session)) -> TagRepository:
    return TagRepository(session)


# Services
def get_pipeline_service(
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
    revision_repo: RevisionRepository = Depends(get_revision_repo),
) -> PipelineService:
    return PipelineService(pipeline_repo, revision_repo=revision_repo)


def get_schema_matrix_service(
    field_freq_repo: FieldFrequencyRepository = Depends(get_field_frequency_repo),
) -> SchemaMatrixService:
    return SchemaMatrixService(field_freq_repo)


def get_ai_service(
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
) -> AIService:
    return AIService(pipeline_repo)


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


def get_tag_service(
    tag_repo: TagRepository = Depends(get_tag_repo),
) -> TagService:
    return TagService(tag_repo)


# ---------------------------------------------------------------------------
# Annotated dependency aliases
# ---------------------------------------------------------------------------

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
