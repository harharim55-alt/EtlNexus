import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.auth import (
    get_current_user,
    require_pipeline_visibility,
    require_team_membership,
)
from app.config import is_master_admin, settings
from app.dependencies import (
    get_pipeline_service,
    get_revision_repo,
)
from app.models.user import User
from app.repositories.revision_repo import RevisionRepository
from app.schemas.common import SuccessResponse
from app.schemas.pipeline import (
    JoinSuggestionsResponse,
    PipelineDetail,
    PipelineFieldSchema,
    PipelineListResponse,
    PipelineRevisionResponse,
    PipelineUpdateRequest,
    PipelineUpdateResponse,
    RevisionListResponse,
)
from app.services.pipeline_service import DuplicateProductNameError, PipelineService

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


@router.get("", response_model=PipelineListResponse)
async def list_pipelines(
    q: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(settings.default_page_limit, ge=1, le=500),
    team: list[str] | None = Query(None),
    schedule: list[str] | None = Query(None),
    is_data_product: bool | None = Query(None),
    is_tag: bool | None = Query(None),
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
):
    is_admin = user.role == "admin"
    user_team_ids = (
        {ut.team_id for ut in (user.team_memberships or [])}
        if not is_admin
        else None
    )
    return await service.list_pipelines(
        query=q,
        user_id=user.id,
        user_team_ids=user_team_ids,
        is_admin=is_admin,
        skip=skip,
        limit=limit,
        team_names=team,
        schedule_types=schedule,
        is_data_product=is_data_product,
        is_tag=is_tag,
    )


@router.get("/{pipeline_id}", response_model=PipelineDetail)
async def get_pipeline(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
):
    user_team_ids = {ut.team_id for ut in (user.team_memberships or [])}

    result = await service.get_pipeline_detail_for_user(
        pipeline_id=pipeline_id,
        user_id=user.id,
        user_team_ids=user_team_ids,
        user_role=user.role,
        is_master=is_master_admin(user.display_name),
    )
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


@router.patch(
    "/{pipeline_id}",
    response_model=PipelineUpdateResponse,
    dependencies=[Depends(require_team_membership("pipeline_id"))],
)
async def update_pipeline(
    request: Request,
    pipeline_id: uuid.UUID,
    body: PipelineUpdateRequest,
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
    revision_repo: RevisionRepository = Depends(get_revision_repo),
):
    # Reuse pipeline loaded by require_team_membership
    preloaded = getattr(request.state, "pipeline", None)
    result = await service.update_pipeline_metadata(
        pipeline_id,
        body,
        updated_by=user.display_name,
        preloaded_pipeline=preloaded,
        revision_repo=revision_repo,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


@router.get("/{pipeline_id}/revisions", response_model=RevisionListResponse, dependencies=[Depends(require_pipeline_visibility())])
async def list_revisions(
    pipeline_id: uuid.UUID,
    field: str | None = Query(None, pattern="^(description|documentation)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    revision_repo: RevisionRepository = Depends(get_revision_repo),
):
    items, total = await revision_repo.list_by_pipeline(
        pipeline_id, field_name=field, skip=skip, limit=limit
    )
    return RevisionListResponse(
        items=[PipelineRevisionResponse.model_validate(r) for r in items],
        total=total,
    )


@router.post(
    "/{pipeline_id}/revisions/{revision_id}/restore",
    response_model=PipelineUpdateResponse,
    dependencies=[Depends(require_team_membership("pipeline_id"))],
)
async def restore_revision(
    pipeline_id: uuid.UUID,
    revision_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
    revision_repo: RevisionRepository = Depends(get_revision_repo),
):
    result = await service.restore_revision(
        pipeline_id,
        revision_id,
        restored_by=user.display_name,
        revision_repo=revision_repo,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline or revision not found")
    return result


@router.get("/{pipeline_id}/joins", response_model=JoinSuggestionsResponse)
async def get_join_suggestions(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
):
    is_admin = user.role == "admin"
    user_team_ids = {ut.team_id for ut in (user.team_memberships or [])}
    result = await service.get_join_suggestions(
        pipeline_id=pipeline_id,
        user_id=user.id,
        user_team_ids=user_team_ids,
        is_admin=is_admin,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


# ---------- Schema manual override ----------


class ManualFieldsRequest(BaseModel):
    fields: list[PipelineFieldSchema]


@router.put(
    "/{pipeline_id}/fields",
    response_model=SuccessResponse,
    dependencies=[Depends(require_team_membership("pipeline_id"))],
)
async def set_pipeline_fields(
    pipeline_id: uuid.UUID,
    body: ManualFieldsRequest,
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
):
    """Manually set pipeline fields, overriding the Spark Connect catalog sync."""
    result = await service.set_manual_fields(pipeline_id, body.fields, updated_by=user.display_name)
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return SuccessResponse()


# ---------- Data product creation ----------


class DataProductCreateRequest(BaseModel):
    name: str
    description: str | None = None
    documentation: str | None = None
    schedule_type: str | None = None
    is_tag: bool = False


data_product_router = APIRouter(prefix="/api/data-products", tags=["data-products"])


@data_product_router.post("", response_model=PipelineDetail, status_code=201)
async def create_data_product(
    body: DataProductCreateRequest,
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
):
    """Create a data product (or a tag, when is_tag=true) owned by the creator's team.

    Only team members (and admins/master admins) may create; viewers cannot. The
    product belongs to the creator's first team. A regular product's schema +
    consume auto-fill from Spark Connect by name; a tag has no schema.
    """
    is_privileged = user.role == "admin" or is_master_admin(user.display_name)
    if not is_privileged and user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot create data products")

    team_id = user.team_memberships[0].team_id if user.team_memberships else None
    if not is_privileged and team_id is None:
        raise HTTPException(status_code=403, detail="You must belong to a team to create a data product")

    try:
        return await service.create_data_product(
            name=body.name,
            description=body.description,
            documentation=body.documentation,
            team_id=team_id,
            schedule_type=body.schedule_type,
            created_by=user.display_name,
            is_tag=body.is_tag,
        )
    except DuplicateProductNameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@data_product_router.post(
    "/from-pipeline/{pipeline_id}",
    response_model=PipelineDetail,
    dependencies=[Depends(require_team_membership("pipeline_id"))],
)
async def promote_to_data_product(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
):
    """Promote an existing pipeline to a data product."""
    result = await service.promote_to_data_product(pipeline_id, promoted_by=user.display_name)
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result
