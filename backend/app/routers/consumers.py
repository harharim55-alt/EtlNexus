from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_pipeline_visibility_by_name
from app.dependencies import get_consumer_service
from app.models.user import User
from app.schemas.consumer import PipelineConsumersResponse
from app.services.consumer_service import ConsumerService

router = APIRouter(prefix="/api/consumers", tags=["consumers"])


@router.get("/{etl_name}", response_model=PipelineConsumersResponse, dependencies=[Depends(require_pipeline_visibility_by_name("etl_name"))])
async def get_pipeline_consumers(
    etl_name: str,
    user: User = Depends(get_current_user),
    service: ConsumerService = Depends(get_consumer_service),
):
    return await service.get_pipeline_consumers(etl_name)
