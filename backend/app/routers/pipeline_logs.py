"""Pipeline log endpoints — CRUD for multi-log data structure."""

import uuid

from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_team_membership_or_editor_grant
from app.dependencies import get_pipeline_log_service
from app.models.user import User
from app.schemas.pipeline_log import (
    LogCreateRequest,
    LogFieldSetRequest,
    LogListResponse,
    LogNetworkSetRequest,
    LogResponse,
    LogUpdateRequest,
)
from app.services.pipeline_log_service import PipelineLogService

router = APIRouter(prefix="/api/pipelines", tags=["pipeline-logs"])


@router.get("/{pipeline_id}/logs", response_model=LogListResponse)
async def list_logs(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PipelineLogService = Depends(get_pipeline_log_service),
):
    logs = await service.list_logs(pipeline_id)
    return LogListResponse(items=logs)


@router.post(
    "/{pipeline_id}/logs",
    response_model=LogResponse,
    status_code=201,
    dependencies=[Depends(require_team_membership_or_editor_grant("pipeline_id"))],
)
async def create_log(
    pipeline_id: uuid.UUID,
    body: LogCreateRequest,
    user: User = Depends(get_current_user),
    service: PipelineLogService = Depends(get_pipeline_log_service),
):
    return await service.create_log(pipeline_id, body.name, body.ordinal_position)


@router.patch(
    "/{pipeline_id}/logs/{log_id}",
    response_model=LogResponse,
    dependencies=[Depends(require_team_membership_or_editor_grant("pipeline_id"))],
)
async def update_log(
    pipeline_id: uuid.UUID,
    log_id: uuid.UUID,
    body: LogUpdateRequest,
    user: User = Depends(get_current_user),
    service: PipelineLogService = Depends(get_pipeline_log_service),
):
    return await service.update_log(log_id, **body.model_dump(exclude_unset=True))


@router.delete(
    "/{pipeline_id}/logs/{log_id}",
    status_code=204,
    dependencies=[Depends(require_team_membership_or_editor_grant("pipeline_id"))],
)
async def delete_log(
    pipeline_id: uuid.UUID,
    log_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PipelineLogService = Depends(get_pipeline_log_service),
):
    await service.delete_log(log_id)


@router.put(
    "/{pipeline_id}/logs/{log_id}/networks",
    response_model=LogResponse,
    dependencies=[Depends(require_team_membership_or_editor_grant("pipeline_id"))],
)
async def set_log_networks(
    pipeline_id: uuid.UUID,
    log_id: uuid.UUID,
    body: LogNetworkSetRequest,
    user: User = Depends(get_current_user),
    service: PipelineLogService = Depends(get_pipeline_log_service),
):
    networks = [{"network_id": n.network_id, "retention": n.retention} for n in body.networks]
    return await service.set_log_networks(log_id, networks)


@router.put(
    "/{pipeline_id}/logs/{log_id}/fields",
    response_model=LogResponse,
    dependencies=[Depends(require_team_membership_or_editor_grant("pipeline_id"))],
)
async def set_log_fields(
    pipeline_id: uuid.UUID,
    log_id: uuid.UUID,
    body: LogFieldSetRequest,
    user: User = Depends(get_current_user),
    service: PipelineLogService = Depends(get_pipeline_log_service),
):
    fields = [{"name": f.name, "data_type": f.data_type, "ordinal_position": f.ordinal_position} for f in body.fields]
    return await service.set_log_fields(log_id, fields)
