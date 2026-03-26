"""Resource & performance metrics endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user
from app.dependencies import get_resource_service
from app.models.user import User
from app.schemas.date_range import DateRangeParams
from app.schemas.execution_plan import ExecutionPlanResponse, ExecutionPlanRunsResponse
from app.schemas.resources import (
    PipelineRunDetail,
    PipelineRunsResponse,
    ResourceHistoryResponse,
    ResourceMetricsResponse,
)
from app.services.resource_service import ResourceService

router = APIRouter(prefix="/api/pipelines", tags=["resources"])


@router.get("/{pipeline_id}/resources", response_model=ResourceMetricsResponse)
async def get_pipeline_resources(
    pipeline_id: uuid.UUID,
    dates: DateRangeParams = Depends(),
    user: User = Depends(get_current_user),
    service: ResourceService = Depends(get_resource_service),
):
    result = await service.get_resource_metrics(
        pipeline_id, date_from=dates.date_from, date_to=dates.date_to,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


@router.get("/{pipeline_id}/resources/history", response_model=ResourceHistoryResponse)
async def get_resource_history(
    pipeline_id: uuid.UUID,
    dates: DateRangeParams = Depends(),
    user: User = Depends(get_current_user),
    service: ResourceService = Depends(get_resource_service),
):
    result = await service.get_resource_history(
        pipeline_id, date_from=dates.date_from, date_to=dates.date_to,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


# ── Execution plan routes (must come BEFORE /runs/{dag_run_id} catch-all) ──


@router.get("/{pipeline_id}/execution-plan", response_model=ExecutionPlanResponse)
async def get_execution_plan(
    pipeline_id: uuid.UUID,
    dag_run_id: str | None = Query(None, description="Specific DAG run ID to fetch plan for"),
    user: User = Depends(get_current_user),
    service: ResourceService = Depends(get_resource_service),
):
    result = await service.get_execution_plan(pipeline_id, dag_run_id=dag_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No execution plan found")
    return result


@router.get("/{pipeline_id}/execution-plan/runs", response_model=ExecutionPlanRunsResponse)
async def list_execution_plan_runs(
    pipeline_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: ResourceService = Depends(get_resource_service),
):
    return await service.get_execution_plan_runs(pipeline_id, skip=skip, limit=limit)


# ── Run-centric routes (catch-all {dag_run_id} must be last) ──


@router.get("/{pipeline_id}/runs", response_model=PipelineRunsResponse)
async def list_pipeline_runs(
    pipeline_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: ResourceService = Depends(get_resource_service),
):
    return await service.get_pipeline_runs(pipeline_id, skip=skip, limit=limit)


@router.get("/{pipeline_id}/runs/{dag_run_id}", response_model=PipelineRunDetail)
async def get_pipeline_run_detail(
    pipeline_id: uuid.UUID,
    dag_run_id: str,
    user: User = Depends(get_current_user),
    service: ResourceService = Depends(get_resource_service),
):
    result = await service.get_run_detail(pipeline_id, dag_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return result
