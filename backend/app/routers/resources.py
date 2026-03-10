"""Resource & performance metrics endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_resource_service
from app.schemas.resources import ResourceMetricsResponse
from app.services.resource_service import ResourceService

router = APIRouter(prefix="/api/pipelines", tags=["resources"])


@router.get("/{pipeline_id}/resources", response_model=ResourceMetricsResponse)
async def get_pipeline_resources(
    pipeline_id: uuid.UUID,
    service: ResourceService = Depends(get_resource_service),
):
    result = await service.get_resource_metrics(pipeline_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result
