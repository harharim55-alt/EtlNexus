import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth import get_current_user, require_team_membership, require_team_membership_or_editor_grant
from app.dependencies import (
    get_airflow_sync_service,
    get_pipeline_repo,
    get_pipeline_service,
    get_visibility_grant_repo,
)
from app.repositories.pipeline_repo import PipelineRepository
from app.models.user import User
from app.repositories.visibility_grant_repo import VisibilityGrantRepository
from app.schemas.pipeline import (
    JoinSuggestionsResponse,
    PipelineDetail,
    PipelineListResponse,
    PipelineUpdateRequest,
    PipelineUpdateResponse,
    SyncResponse,
)
from app.services.airflow_sync_service import AirflowSyncService
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


@router.get("", response_model=PipelineListResponse)
async def list_pipelines(
    q: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
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
):
    # Reuse pipeline loaded by require_team_membership_or_editor_grant
    preloaded = getattr(request.state, "pipeline", None)
    result = await service.update_pipeline_metadata(
        pipeline_id, body, updated_by=user.display_name, preloaded_pipeline=preloaded
    )
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


@router.post(
    "/{pipeline_id}/sync",
    response_model=SyncResponse,
    dependencies=[Depends(require_team_membership("pipeline_id"))],
)
async def sync_pipeline(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: AirflowSyncService = Depends(get_airflow_sync_service),
):
    try:
        result = await service.sync_single_pipeline(pipeline_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{pipeline_id}/joins", response_model=JoinSuggestionsResponse)
async def get_join_suggestions(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
    grant_repo: VisibilityGrantRepository = Depends(get_visibility_grant_repo),
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
):
    if user.role != "admin":
        pipeline = await pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        user_team_ids = {ut.team_id for ut in (user.team_memberships or [])}
        can_see = await grant_repo.user_can_see_pipeline(
            pipeline_id=pipeline_id,
            pipeline_team_id=pipeline.team_id,
            user_id=user.id,
            user_team_ids=user_team_ids,
        )
        if not can_see:
            raise HTTPException(status_code=404, detail="Pipeline not found")
    result = await service.get_join_suggestions(pipeline_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result
