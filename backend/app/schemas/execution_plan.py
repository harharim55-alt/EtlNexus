"""Execution plan DTOs — recursive tree structure from Spark physical plans."""

from __future__ import annotations

from pydantic import BaseModel


class ExecutionPlanNode(BaseModel):
    id: int
    name: str
    type: str  # "read", "write", "shuffle", "transform"
    detail: str
    full_detail: str = ""
    metrics: dict[str, str] = {}
    children: list[ExecutionPlanNode] = []
    is_bottleneck: bool = False
    bottleneck_reason: str | None = None


class ExecutionPlanRunSummary(BaseModel):
    dag_run_id: str
    dag_id: str
    start_date: str | None = None
    status: str


class ExecutionPlanRunsResponse(BaseModel):
    items: list[ExecutionPlanRunSummary] = []
    total: int = 0


class ExecutionPlanResponse(BaseModel):
    dag_id: str
    dag_run_id: str
    task_id: str
    status: str
    duration_seconds: float | None = None
    execution_date: str | None = None
    execution_plan: ExecutionPlanNode | None = None
    plan_hash: str | None = None
    plan_stability: str | None = None


class PlanDiffNode(BaseModel):
    name: str
    type: str
    status: str = "unchanged"
    metrics_before: dict[str, str] | None = None
    metrics_after: dict[str, str] | None = None
    children: list[PlanDiffNode] = []


class PlanDiffResponse(BaseModel):
    base_run_id: str
    compare_run_id: str
    plan_changed: bool
    diff: PlanDiffNode | None = None
    summary: str
