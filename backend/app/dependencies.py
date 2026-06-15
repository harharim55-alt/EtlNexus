from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db_session
from app.models.user import User
from app.repositories.catalog_mirror_repo import CatalogMirrorRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.revision_repo import RevisionRepository
from app.repositories.team_repo import TeamRepository
from app.repositories.user_repo import UserRepository
from app.services.ai_service import AIService
from app.services.pipeline_service import PipelineService
from app.services.table_service import TableService


# Repositories
def get_pipeline_repo(session: AsyncSession = Depends(get_db_session)) -> PipelineRepository:
    return PipelineRepository(session)


def get_revision_repo(session: AsyncSession = Depends(get_db_session)) -> RevisionRepository:
    return RevisionRepository(session)


def get_user_repo(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    return UserRepository(session)


def get_team_repo(session: AsyncSession = Depends(get_db_session)) -> TeamRepository:
    return TeamRepository(session)


def get_mirror_repo(session: AsyncSession = Depends(get_db_session)) -> CatalogMirrorRepository:
    return CatalogMirrorRepository(session)


# Services
def get_pipeline_service(
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
    revision_repo: RevisionRepository = Depends(get_revision_repo),
) -> PipelineService:
    return PipelineService(pipeline_repo, revision_repo=revision_repo)


def get_ai_service(
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
) -> AIService:
    return AIService(pipeline_repo)


def get_table_service(
    mirror_repo: CatalogMirrorRepository = Depends(get_mirror_repo),
) -> TableService:
    return TableService(mirror_repo)


# ---------------------------------------------------------------------------
# Annotated dependency aliases
# ---------------------------------------------------------------------------

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
