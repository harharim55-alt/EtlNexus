"""Resource & performance metric DTOs."""

from datetime import datetime

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
    spark_application_id: str | None = None
    metrics_source: str | None = None


class ActualUsage(BaseModel):
    avg_driver_memory_used_mb: int | None = None
    avg_executor_memory_peak_mb: int | None = None
    avg_cpu_utilization_pct: float | None = None
    avg_executors_active: int | None = None
    # sparkMeasure extended metrics
    avg_jvm_gc_time_ms: int | None = None
    avg_shuffle_read_bytes: int | None = None
    avg_shuffle_write_bytes: int | None = None
    avg_input_bytes: int | None = None
    avg_output_bytes: int | None = None
    avg_memory_bytes_spilled: int | None = None
    avg_disk_bytes_spilled: int | None = None
    avg_peak_execution_memory: int | None = None
    # Peak (max) values across runs
    peak_driver_memory_used_mb: int | None = None
    peak_executor_memory_mb: int | None = None
    peak_cpu_utilization_pct: float | None = None
    peak_executors_active: int | None = None
    peak_execution_memory: int | None = None
    metrics_source: str | None = None


class ResourceRecommendation(BaseModel):
    resource: str
    current_value: str
    recommended_value: str
    reason: str
    severity: str = "info"


class TrendAnalysis(BaseModel):
    metric: str
    direction: str  # "increasing", "decreasing", "stable"
    slope_per_day: float
    confidence: float
    message: str


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

    # Percentile stats
    p50_duration_seconds: float | None = None
    p95_duration_seconds: float | None = None
    p99_duration_seconds: float | None = None
    p95_driver_memory_mb: float | None = None
    p95_executor_memory_mb: float | None = None
    p95_cpu_pct: float | None = None

    # Insights
    recommendations: list[ResourceRecommendation] = []
    trends: list[TrendAnalysis] = []
    input_data_correlation: float | None = None
    avg_input_bytes: float | None = None


class ResourceHistoryRecord(BaseModel):
    execution_date: str | None = None
    dag_id: str = ""
    dag_run_id: str = ""
    status: str = "unknown"
    duration_seconds: float | None = None
    driver_memory_used_mb: int | None = None
    executor_memory_peak_mb: int | None = None
    cpu_utilization_pct: float | None = None
    executors_active: int | None = None
    peak_execution_memory: int | None = None
    jvm_gc_time_ms: int | None = None
    shuffle_read_bytes: int | None = None
    shuffle_write_bytes: int | None = None
    input_bytes: int | None = None
    output_bytes: int | None = None
    memory_bytes_spilled: int | None = None
    disk_bytes_spilled: int | None = None
    metrics_source: str | None = None


class ResourceHistoryResponse(BaseModel):
    records: list[ResourceHistoryRecord] = []
    total: int = 0


# ── Run-centric schemas ──────────────────────────────────────────────


class PipelineRunItem(BaseModel):
    dag_run_id: str
    dag_id: str
    status: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    duration_seconds: float | None = None
    has_execution_plan: bool = False
    failure_reason: str | None = None


class PipelineRunsResponse(BaseModel):
    items: list[PipelineRunItem] = []
    total: int = 0


class FieldSnapshot(BaseModel):
    name: str
    data_type: str | None = None
    ordinal_position: int = 0


class PipelineRunDetail(BaseModel):
    """Full detail for a single run — resource metrics + snapshots."""

    dag_run_id: str
    dag_id: str
    status: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    duration_seconds: float | None = None
    # Resource metrics
    driver_memory_used_mb: int | None = None
    executor_memory_peak_mb: int | None = None
    cpu_utilization_pct: float | None = None
    executors_active: int | None = None
    peak_execution_memory: int | None = None
    jvm_gc_time_ms: int | None = None
    shuffle_read_bytes: int | None = None
    shuffle_write_bytes: int | None = None
    input_bytes: int | None = None
    output_bytes: int | None = None
    memory_bytes_spilled: int | None = None
    disk_bytes_spilled: int | None = None
    metrics_source: str | None = None
    spark_application_id: str | None = None
    has_execution_plan: bool = False
    # Per-run snapshots
    fields_snapshot: list[FieldSnapshot] | None = None
    source_tables_snapshot: list[str] | None = None
    destination_tables_snapshot: list[str] | None = None
    failure_reason: str | None = None
