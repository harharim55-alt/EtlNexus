import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, require_role
from app.database import async_session_factory
from app.dependencies import get_airflow_repo
from app.integrations.airflow_client import airflow_client
from app.models.user import User
from app.repositories.airflow_repo import AirflowRepository
from app.schemas.airflow import AirflowStatusesResponse, AirflowStatusSchema
from app.services.airflow_sync_service import AirflowSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/airflow", tags=["airflow"])


@router.get("/status", response_model=AirflowStatusesResponse)
async def get_all_statuses(
    user: User = Depends(get_current_user),
    repo: AirflowRepository = Depends(get_airflow_repo),
):
    statuses = await repo.get_all()
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

        from app.cache import clear_all
        clear_all()
        return SyncAllResponse(synced=count, message=f"Synced {count} pipelines from Airflow")
    except Exception as e:
        logger.exception("Manual full sync failed")
        raise HTTPException(status_code=500, detail=str(e))
