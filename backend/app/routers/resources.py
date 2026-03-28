"""Resource & performance metrics endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, require_pipeline_visibility
from app.dependencies import get_resource_service
from app.models.user import User
from app.schemas.date_range import DateRangeParams
from app.schemas.execution_plan import ExecutionPlanResponse, ExecutionPlanRunsResponse, PlanDiffResponse
from app.schemas.resources import (
    PipelineRunDetail,
    PipelineRunsResponse,
    ResourceHistoryResponse,
    ResourceMetricsResponse,
)
from app.services.resource_service import ResourceService

router = APIRouter(prefix="/api/pipelines", tags=["resources"])


@router.get("/{pipeline_id}/resources", response_model=ResourceMetricsResponse, dependencies=[Depends(require_pipeline_visibility())])
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


@router.get("/{pipeline_id}/resources/history", response_model=ResourceHistoryResponse, dependencies=[Depends(require_pipeline_visibility())])
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


@router.get("/{pipeline_id}/execution-plan", response_model=ExecutionPlanResponse, dependencies=[Depends(require_pipeline_visibility())])
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


@router.get("/{pipeline_id}/execution-plan/diff", response_model=PlanDiffResponse)
async def diff_execution_plans(
    pipeline_id: uuid.UUID,
    base_run_id: str = Query(...),
    compare_run_id: str = Query(...),
    user: User = Depends(require_pipeline_visibility()),
    service: ResourceService = Depends(get_resource_service),
) -> PlanDiffResponse:
    """Compare two execution plans for a pipeline and return a structural diff."""
    result = await service.compare_execution_plans(pipeline_id, base_run_id, compare_run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Plans not found")
    return result


@router.get("/{pipeline_id}/execution-plan/runs", response_model=ExecutionPlanRunsResponse, dependencies=[Depends(require_pipeline_visibility())])
async def list_execution_plan_runs(
    pipeline_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: ResourceService = Depends(get_resource_service),
):
    return await service.get_execution_plan_runs(pipeline_id, skip=skip, limit=limit)


# ── Run-centric routes (catch-all {dag_run_id} must be last) ──


@router.get("/{pipeline_id}/runs", response_model=PipelineRunsResponse, dependencies=[Depends(require_pipeline_visibility())])
async def list_pipeline_runs(
    pipeline_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: ResourceService = Depends(get_resource_service),
):
    return await service.get_pipeline_runs(pipeline_id, skip=skip, limit=limit)


@router.get("/{pipeline_id}/runs/{dag_run_id}", response_model=PipelineRunDetail, dependencies=[Depends(require_pipeline_visibility())])
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
