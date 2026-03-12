import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_team_membership_or_editor_grant
from app.dependencies import (
    get_airflow_sync_service,
    get_pipeline_service,
    get_visibility_grant_repo,
)
from app.models.user import User
from app.repositories.visibility_grant_repo import VisibilityGrantRepository
from app.schemas.pipeline import (
    JoinSuggestionsResponse,
    PipelineDetail,
    PipelineListItem,
    PipelineUpdateRequest,
    PipelineUpdateResponse,
    SyncResponse,
)
from app.services.airflow_sync_service import AirflowSyncService
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


@router.get("", response_model=list[PipelineListItem])
async def list_pipelines(
    q: str | None = None,
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
):
    return await service.list_pipelines(query=q, user=user)


@router.get("/{pipeline_id}", response_model=PipelineDetail)
async def get_pipeline(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
    grant_repo: VisibilityGrantRepository = Depends(get_visibility_grant_repo),
):
    result = await service.get_pipeline_detail(pipeline_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Compute can_edit server-side and enforce visibility
    if user.role == "admin":
        result.can_edit = True
    elif not result.team_id:
        result.can_edit = True
    else:
        pipeline_team_uuid = uuid.UUID(result.team_id)
        user_team_ids = {ut.team_id for ut in (user.team_memberships or [])}

        # Enforce visibility — return 404 to prevent UUID enumeration
        can_see = await grant_repo.user_can_see_pipeline(
            pipeline_id=pipeline_id,
            pipeline_team_id=pipeline_team_uuid,
            user_id=user.id,
            user_team_ids=user_team_ids,
        )
        if not can_see:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        if pipeline_team_uuid in user_team_ids:
            result.can_edit = True
        else:
            grant_level = await grant_repo.get_grant_level_for_pipeline(
                pipeline_id=pipeline_id,
                user_id=user.id,
                user_team_ids=user_team_ids,
                pipeline_team_id=pipeline_team_uuid,
            )
            result.can_edit = grant_level == "editor"

    return result


@router.patch(
    "/{pipeline_id}",
    response_model=PipelineUpdateResponse,
    dependencies=[Depends(require_team_membership_or_editor_grant("pipeline_id"))],
)
async def update_pipeline(
    pipeline_id: uuid.UUID,
    body: PipelineUpdateRequest,
    user: User = Depends(get_current_user),
    service: PipelineService = Depends(get_pipeline_service),
):
    result = await service.update_pipeline_metadata(
        pipeline_id, body, updated_by=user.display_name
    )
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


@router.post("/{pipeline_id}/sync", response_model=SyncResponse)
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
):
    result = await service.get_join_suggestions(pipeline_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result
