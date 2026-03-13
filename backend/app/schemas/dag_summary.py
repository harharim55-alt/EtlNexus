"""Pydantic DTOs for DAG summary/statistics endpoint."""

from pydantic import BaseModel


class DagTaskSummary(BaseModel):
    task_id: str
    pipeline_name: str | None = None
    pipeline_id: str | None = None
    status: str
    latest_duration_seconds: float | None = None
    avg_duration_seconds: float | None = None
    task_group_id: str | None = None


class DagSummary(BaseModel):
    dag_id: str
    description: str | None = None
    schedule_interval: str | None = None
    is_paused: bool = False
    task_count: int = 0
    pipeline_count: int = 0

    # Duration aggregates (from latest DAG run)
    total_duration_seconds: float | None = None
    avg_task_duration_seconds: float | None = None
    min_task_duration_seconds: float | None = None
    max_task_duration_seconds: float | None = None

    # Status counts (from current Airflow statuses) — dynamic keys, one per Airflow state
    status_counts: dict[str, int] = {}
    success_rate: float | None = None

    # Timing
    latest_run_start: str | None = None
    latest_run_end: str | None = None
    typical_finish_hour: str | None = None

    # Period-based history (default 30d, adjusts with date range)
    total_runs_30d: int = 0
    dag_success_rate_30d: float | None = None
    period_label: str = "30d"

    tasks: list[DagTaskSummary] = []


class DagSummaryAggregate(BaseModel):
    total_dags: int = 0
    total_pipelines: int = 0
    active_dags: int = 0
    overall_success_rate: float | None = None
    total_runs_30d: int = 0
    period_label: str = "30d"


class DagSummaryResponse(BaseModel):
    aggregate: DagSummaryAggregate
    dags: list[DagSummary] = []
