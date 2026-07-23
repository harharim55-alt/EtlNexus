from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthUser, get_current_user
from app.database import get_db_session
from app.repositories.data_product_repo import DataProductRepository
from app.repositories.iceberg_metrics_repo import IcebergMetricsRepository
from app.repositories.revision_repo import RevisionRepository
from app.services.ai_service import AIService
from app.services.data_product_service import DataProductService
from app.services.table_service import TableService


# Repositories
def get_data_product_repo(session: AsyncSession = Depends(get_db_session)) -> DataProductRepository:
    return DataProductRepository(session)


def get_revision_repo(session: AsyncSession = Depends(get_db_session)) -> RevisionRepository:
    return RevisionRepository(session)


def get_iceberg_metrics_repo(session: AsyncSession = Depends(get_db_session)) -> IcebergMetricsRepository:
    return IcebergMetricsRepository(session)


# Services
def get_data_product_service(
    repo: DataProductRepository = Depends(get_data_product_repo),
    revision_repo: RevisionRepository = Depends(get_revision_repo),
) -> DataProductService:
    return DataProductService(repo, revision_repo=revision_repo)


def get_ai_service(
    repo: DataProductRepository = Depends(get_data_product_repo),
) -> AIService:
    return AIService(repo)


def get_table_service(
    metrics_repo: IcebergMetricsRepository = Depends(get_iceberg_metrics_repo),
) -> TableService:
    return TableService(metrics_repo)


# ---------------------------------------------------------------------------
# Annotated dependency aliases
# ---------------------------------------------------------------------------

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
