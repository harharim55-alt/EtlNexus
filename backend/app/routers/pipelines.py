import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth import get_current_user, require_pipeline_visibility, require_team_membership, require_team_membership_or_editor_grant
from app.config import settings
from app.dependencies import (
    get_airflow_sync_service,
    get_pipeline_service,
    get_revision_repo,
    get_visibility_grant_repo,
)
from app.models.user import User
from app.rate_limit import limiter
from app.repositories.revision_repo import RevisionRepository
from app.repositories.visibility_grant_repo import VisibilityGrantRepository
from app.schemas.date_range import DateRangeParams
from app.schemas.pipeline import (
    JoinSuggestionsResponse,
    PipelineDetail,
    PipelineListResponse,
    PipelineRevisionResponse,
    PipelineUpdateRequest,
    PipelineUpdateResponse,
    RevisionListResponse,
    SyncResponse,
)
from app.services.airflow_sync_service import AirflowSyncService
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


@router.get("", response_model=PipelineListResponse)
async def list_pipelines(
    q: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(settings.default_page_limit, ge=1, le=500),
    dates: DateRangeParams = Depends(),
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
        date_from=dates.date_from,
        date_to=dates.date_to,
    )


@router.get("/{pipeline_id}", response_model=PipelineDetail)
async def get_pipeline(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
    grant_repo: VisibilityGrantRepository = Depends(get_visibility_grant_repo),
):
    is_admin = user.role == "admin"
    user_team_ids = {ut.team_id for ut in (user.team_memberships or [])}

    result = await service.get_pipeline_detail_for_user(
        pipeline_id=pipeline_id,
        user_id=user.id,
        user_team_ids=user_team_ids,
        is_admin=is_admin,
        grant_repo=grant_repo,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


@router.patch(
    "/{pipeline_id}",
    response_model=PipelineUpdateResponse,
    dependencies=[Depends(require_team_membership_or_editor_grant("pipeline_id"))],
)
async def update_pipeline(
    request: Request,
    pipeline_id: uuid.UUID,
    body: PipelineUpdateRequest,
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
    revision_repo: RevisionRepository = Depends(get_revision_repo),
):
    # Reuse pipeline loaded by require_team_membership_or_editor_grant
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


@router.post(
    "/{pipeline_id}/sync",
    response_model=SyncResponse,
    dependencies=[Depends(require_team_membership("pipeline_id"))],
)
@limiter.limit("30/minute")
async def sync_pipeline(
    request: Request,
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: AirflowSyncService = Depends(get_airflow_sync_service),
):
    try:
        result = await service.sync_single_pipeline(pipeline_id)
        from app.cache import clear_all
        clear_all()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


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
    dependencies=[Depends(require_team_membership_or_editor_grant("pipeline_id"))],
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
    grant_repo: VisibilityGrantRepository = Depends(get_visibility_grant_repo),
):
    is_admin = user.role == "admin"
    user_team_ids = {ut.team_id for ut in (user.team_memberships or [])}
    result = await service.get_join_suggestions(
        pipeline_id=pipeline_id,
        user_id=user.id,
        user_team_ids=user_team_ids,
        is_admin=is_admin,
        grant_repo=grant_repo,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result
