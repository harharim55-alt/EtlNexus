"""Tag endpoints — CRUD for user-defined pipeline tags."""

import uuid

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user, require_role, require_team_membership_or_editor_grant
from app.dependencies import get_tag_service
from app.models.user import User
from app.schemas.tag import (
    PipelineTagsRequest,
    TagCreateRequest,
    TagListResponse,
    TagResponse,
)
from app.services.tag_service import TagService

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=TagListResponse)
async def list_tags(
    team_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    service: TagService = Depends(get_tag_service),
):
    tags = await service.list_tags(team_id=team_id)
    return TagListResponse(items=[TagResponse.model_validate(t) for t in tags])


@router.post("", response_model=TagResponse, status_code=201)
async def create_tag(
    body: TagCreateRequest,
    user: User = Depends(get_current_user),
    service: TagService = Depends(get_tag_service),
):
    # Use the first team the user belongs to as the tag creator
    team_id = user.team_memberships[0].team_id if user.team_memberships else None
    tag = await service.create_tag(name=body.name, created_by_team_id=team_id)
    return TagResponse.model_validate(tag)


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    service: TagService = Depends(get_tag_service),
):
    await service.delete_tag(tag_id)


# Pipeline-scoped tag management
pipeline_tag_router = APIRouter(prefix="/api/pipelines", tags=["tags"])


@pipeline_tag_router.get(
    "/{pipeline_id}/tags",
    response_model=TagListResponse,
)
async def get_pipeline_tags(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TagService = Depends(get_tag_service),
):
    tags = await service.list_pipeline_tags(pipeline_id)
    return TagListResponse(items=[TagResponse.model_validate(t) for t in tags])


@pipeline_tag_router.put(
    "/{pipeline_id}/tags",
    response_model=TagListResponse,
    dependencies=[Depends(require_team_membership_or_editor_grant("pipeline_id"))],
)
async def set_pipeline_tags(
    pipeline_id: uuid.UUID,
    body: PipelineTagsRequest,
    user: User = Depends(get_current_user),
    service: TagService = Depends(get_tag_service),
):
    tags = await service.set_pipeline_tags(pipeline_id, body.tag_ids)
    return TagListResponse(items=[TagResponse.model_validate(t) for t in tags])
