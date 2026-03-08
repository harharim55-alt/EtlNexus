from fastapi import APIRouter, Depends

from app.dependencies import get_consumer_service
from app.schemas.consumer import PipelineConsumersResponse
from app.services.consumer_service import ConsumerService

router = APIRouter(prefix="/api/consumers", tags=["consumers"])


@router.get("/{etl_name}", response_model=PipelineConsumersResponse)
async def get_pipeline_consumers(
    etl_name: str,
    service: ConsumerService = Depends(get_consumer_service),
):
    return await service.get_pipeline_consumers(etl_name)
