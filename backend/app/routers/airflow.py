import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_role
from app.database import async_session_factory, get_db_session
from app.dependencies import get_airflow_repo
from app.integrations.airflow_client import airflow_client
from app.models.pipeline import Pipeline
from app.models.user import User
from app.repositories.airflow_repo import AirflowRepository
from app.repositories.visibility_filter import VisibilityFilter
from app.schemas.airflow import AirflowStatusesResponse, AirflowStatusSchema
from app.services.airflow_sync_service import AirflowSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/airflow", tags=["airflow"])


@router.get("/status", response_model=AirflowStatusesResponse)
async def get_all_statuses(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    repo: AirflowRepository = Depends(get_airflow_repo),
) -> AirflowStatusesResponse:
    """Return Airflow run statuses for all (or visible) pipelines.

    Admins see statuses for all pipelines.  Non-admin users see only statuses
    for pipelines visible to them (own team, unassigned, or grant-accessible).
    """
    visible_pipeline_ids: set[uuid.UUID] | None = None

    if user.role != "admin":
        user_team_ids = {ut.team_id for ut in (user.team_memberships or [])}
        visibility_conditions = await VisibilityFilter.build_batch_visibility_conditions(
            session=session,
            user_id=user.id,
            user_team_ids=user_team_ids,
        )
        id_stmt = select(Pipeline.id).where(or_(*visibility_conditions))
        result = await session.execute(id_stmt)
        visible_pipeline_ids = {row[0] for row in result.all()}

    statuses = await repo.get_all(visible_pipeline_ids=visible_pipeline_ids)
    return AirflowStatusesResponse(
        statuses=[
            AirflowStatusSchema(
                pipeline_id=str(s.pipeline_id),
                dag_id=s.dag_id,
                status=s.status,
                execution_date=s.execution_date,
                last_checked_at=s.last_checked_at,
            )
            for s in statuses
        ],
        airflow_connected=airflow_client.is_connected,
    )


@router.get("/status/{pipeline_id}", response_model=AirflowStatusSchema)
async def get_pipeline_status(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    repo: AirflowRepository = Depends(get_airflow_repo),
):
    status = await repo.get_by_pipeline_id(pipeline_id)
    if not status:
        raise HTTPException(status_code=404, detail="No Airflow status found for this pipeline")
    return AirflowStatusSchema(
        pipeline_id=str(status.pipeline_id),
        dag_id=status.dag_id,
        status=status.status,
        execution_date=status.execution_date,
        last_checked_at=status.last_checked_at,
    )


class SyncAllResponse(BaseModel):
    synced: int
    message: str


@router.post(
    "/sync-all",
    response_model=SyncAllResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def sync_all_pipelines(
    user: User = Depends(get_current_user),
):
    """Trigger a full pipeline sync + status poll from Airflow (admin only)."""
    logger.info("Admin %s triggered full Airflow sync", user.email)
    try:
        async with async_session_factory() as session:
            service = AirflowSyncService(session)
            count = await service.sync_pipelines_from_airflow()

        # Poll statuses, run history, resource actuals, and execution plans
        async with async_session_factory() as session:
            from app.repositories.bouncer_repo import BouncerRepository
            from app.repositories.pipeline_repo import PipelineRepository
            from app.repositories.resource_repo import ResourceRepository
            from app.services.airflow_service import AirflowService

            poll_service = AirflowService(
                session,
                airflow_repo=AirflowRepository(session),
                pipeline_repo=PipelineRepository(session),
                resource_repo=ResourceRepository(session),
                bouncer_repo=BouncerRepository(session),
            )
            await poll_service.poll_all_statuses()

        # Sync Iceberg catalog schemas (now that pipelines exist)
        async with async_session_factory() as session:
            from app.services.catalog_sync_service import CatalogSyncService
            catalog_svc = CatalogSyncService(session)
            schema_count = await catalog_svc.sync_from_catalog()
            logger.info("Catalog sync after manual sync: %d pipelines with schemas", schema_count)

        from app.cache import clear_all
        clear_all()
        return SyncAllResponse(synced=count, message=f"Synced {count} pipelines from Airflow ({schema_count} with schemas)")
    except Exception as exc:
        logger.exception("Manual full sync failed")
        raise HTTPException(
            status_code=500,
            detail="Pipeline sync failed. Check server logs for details.",
        ) from exc
