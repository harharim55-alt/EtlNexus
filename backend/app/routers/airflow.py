import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.dependencies import get_airflow_repo
from app.models.user import User
from app.integrations.airflow_client import airflow_client
from app.repositories.airflow_repo import AirflowRepository
from app.schemas.airflow import AirflowStatusesResponse, AirflowStatusSchema

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
