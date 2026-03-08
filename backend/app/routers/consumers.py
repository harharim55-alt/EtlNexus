import uuid

from fastapi import APIRouter, Depends

from app.dependencies import get_consumer_service
from app.schemas.consumer import PipelineConsumersResponse
from app.services.consumer_service import ConsumerService

router = APIRouter(prefix="/api/pipelines", tags=["consumers"])


@router.get("/{pipeline_id}/consumers", response_model=PipelineConsumersResponse)
async def get_pipeline_consumers(
    pipeline_id: uuid.UUID,
    service: ConsumerService = Depends(get_consumer_service),
):
    return await service.get_pipeline_consumers(pipeline_id)
