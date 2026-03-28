import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_pipeline_visibility
from app.dependencies import get_lineage_service
from app.models.user import User
from app.schemas.lineage import LineageGraphSchema
from app.services.lineage_service import LineageService

router = APIRouter(prefix="/api/pipelines", tags=["lineage"])


@router.get("/{pipeline_id}/lineage", response_model=LineageGraphSchema, dependencies=[Depends(require_pipeline_visibility())])
async def get_pipeline_lineage(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: LineageService = Depends(get_lineage_service),
):
    result = await service.build_lineage_graph(pipeline_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result
