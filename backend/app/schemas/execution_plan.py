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
