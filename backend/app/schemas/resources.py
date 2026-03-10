"""Resource & performance metric DTOs."""

from pydantic import BaseModel


class ResourceConfigEntry(BaseModel):
    dag_id: str
    spark_driver_memory: str | None = None
    spark_executor_memory: str | None = None
    spark_executor_cores: int | None = None
    spark_num_executors: int | None = None
    is_dag_override: bool = False


class DurationRun(BaseModel):
    duration_seconds: float
    execution_date: str | None = None
    status: str = "unknown"
    dag_id: str = ""


class ActualUsage(BaseModel):
    avg_driver_memory_used_mb: int | None = None
    avg_executor_memory_peak_mb: int | None = None
    avg_cpu_utilization_pct: float | None = None
    avg_executors_active: int | None = None


class CapacityBar(BaseModel):
    label: str
    allocated: str
    used: str
    max_capacity: str
    allocated_pct: float
    used_pct: float


class ResourceMetricsResponse(BaseModel):
    # Duration stats
    avg_duration_seconds: float | None = None
    min_duration_seconds: float | None = None
    max_duration_seconds: float | None = None
    latest_duration_seconds: float | None = None
    recent_runs: list[DurationRun] = []
    run_count: int = 0
    success_rate: float | None = None

    # Allocated config (per DAG)
    resource_configs: list[ResourceConfigEntry] = []

    # Actual usage (averaged from recent runs)
    actual_usage: ActualUsage = ActualUsage()

    # Capacity utilization (allocated + used vs cluster max)
    capacity: list[CapacityBar] = []
