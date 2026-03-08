import uuid

from fastapi import APIRouter, Depends

from app.dependencies import get_usage_service
from app.schemas.usage import PipelineUsageResponse
from app.services.usage_service import UsageService

router = APIRouter(prefix="/api/pipelines", tags=["usage"])


@router.get("/{pipeline_id}/usage", response_model=PipelineUsageResponse)
async def get_pipeline_usage(
    pipeline_id: uuid.UUID,
    service: UsageService = Depends(get_usage_service),
):
    return await service.get_pipeline_usage(pipeline_id)
