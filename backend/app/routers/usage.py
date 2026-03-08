from fastapi import APIRouter, Depends

from app.dependencies import get_usage_service
from app.schemas.usage import PipelineUsageResponse
from app.services.usage_service import UsageService

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/{etl_name}", response_model=PipelineUsageResponse)
async def get_pipeline_usage(
    etl_name: str,
    service: UsageService = Depends(get_usage_service),
):
    return await service.get_pipeline_usage(etl_name)
