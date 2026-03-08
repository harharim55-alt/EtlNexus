import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_pipeline_service
from app.schemas.pipeline import (
    JoinSuggestionsResponse,
    PipelineDetail,
    PipelineListItem,
)
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


@router.get("/{pipeline_id}/joins", response_model=JoinSuggestionsResponse)
async def get_join_suggestions(
    pipeline_id: uuid.UUID,
    service: PipelineService = Depends(get_pipeline_service),
):
    result = await service.get_join_suggestions(pipeline_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result
