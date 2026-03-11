import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_airflow_sync_service, get_pipeline_service
from app.schemas.pipeline import (
    JoinSuggestionsResponse,
    PipelineDetail,
    PipelineListItem,
    PipelineUpdateRequest,
    PipelineUpdateResponse,
    SyncResponse,
)
from app.services.airflow_sync_service import AirflowSyncService
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


@router.get("", response_model=list[PipelineListItem])
async def list_pipelines(
    q: str | None = None,
    service: PipelineService = Depends(get_pipeline_service),
):
    return await service.list_pipelines(query=q)


@router.get("/{pipeline_id}", response_model=PipelineDetail)
async def get_pipeline(
    pipeline_id: uuid.UUID,
    service: PipelineService = Depends(get_pipeline_service),
):
    result = await service.get_pipeline_detail(pipeline_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


@router.patch("/{pipeline_id}", response_model=PipelineUpdateResponse)
async def update_pipeline(
    pipeline_id: uuid.UUID,
    body: PipelineUpdateRequest,
    service: PipelineService = Depends(get_pipeline_service),
):
    result = await service.update_pipeline_metadata(pipeline_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


@router.post("/{pipeline_id}/sync", response_model=SyncResponse)
async def sync_pipeline(
    pipeline_id: uuid.UUID,
    service: AirflowSyncService = Depends(get_airflow_sync_service),
):
    try:
        result = await service.sync_single_pipeline(pipeline_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{pipeline_id}/joins", response_model=JoinSuggestionsResponse)
async def get_join_suggestions(
    pipeline_id: uuid.UUID,
    service: PipelineService = Depends(get_pipeline_service),
):
    result = await service.get_join_suggestions(pipeline_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result
