"""Tag endpoints. Tags are data products (Pipeline with is_tag); these endpoints
list tags, get/set the tags applied to a product, and list a tag's members.
Creating a tag goes through POST /api/data-products with is_tag=true."""

import uuid

from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_team_membership
from app.dependencies import get_tag_service
from app.models.user import User
from app.schemas.pipeline import PipelineListItem
from app.schemas.tag import PipelineTagsRequest, TagListResponse, TagResponse
from app.services.tag_service import TagService

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=TagListResponse)
async def list_tags(
    user: User = Depends(get_current_user),
    service: TagService = Depends(get_tag_service),
):
    """List all tag-products (for the tag picker)."""
    tags = await service.list_tags()
    return TagListResponse(items=[TagResponse.model_validate(t) for t in tags])


# Pipeline-scoped tag management
pipeline_tag_router = APIRouter(prefix="/api/pipelines", tags=["tags"])


@pipeline_tag_router.get("/{pipeline_id}/tags", response_model=TagListResponse)
async def get_pipeline_tags(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TagService = Depends(get_tag_service),
):
    """Tags applied to a product."""
    tags = await service.tags_for_product(pipeline_id)
    return TagListResponse(items=[TagResponse.model_validate(t) for t in tags])


@pipeline_tag_router.put(
    "/{pipeline_id}/tags",
    response_model=TagListResponse,
    dependencies=[Depends(require_team_membership("pipeline_id"))],
)
async def set_pipeline_tags(
    pipeline_id: uuid.UUID,
    body: PipelineTagsRequest,
    user: User = Depends(get_current_user),
    service: TagService = Depends(get_tag_service),
):
    """Replace the tags applied to a product (editors of that product only)."""
    tags = await service.set_product_tags(pipeline_id, body.tag_ids)
    return TagListResponse(items=[TagResponse.model_validate(t) for t in tags])


@pipeline_tag_router.get("/{pipeline_id}/members", response_model=list[PipelineListItem])
async def get_tag_members(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TagService = Depends(get_tag_service),
) -> list[PipelineListItem]:
    """Products tagged with the given tag (the tag detail page's sub-product tabs)."""
    members = await service.members_of_tag(pipeline_id)
    return [
        PipelineListItem(
            id=m.id,
            name=m.name,
            description=m.description,
            schedule_type=m.schedule_type,
            team=m.team,
            is_data_product=m.is_data_product,
            is_tag=m.is_tag,
        )
        for m in members
    ]
