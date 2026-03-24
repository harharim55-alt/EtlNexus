export interface ResourceConfigEntry {
  dag_id: string;
  spark_driver_memory: string | null;
  spark_executor_memory: string | null;
  spark_executor_cores: number | null;
  spark_num_executors: number | null;
  is_dag_override: boolean;
}

export interface DurationRun {
  duration_seconds: number;
  execution_date: string | null;
  status: string;
  dag_id: string;
  spark_application_id: string | null;
  metrics_source: string | null;
}

export interface ActualUsage {
  avg_driver_memory_used_mb: number | null;
  avg_executor_memory_peak_mb: number | null;
  avg_cpu_utilization_pct: number | null;
  avg_executors_active: number | null;
  // sparkMeasure extended metrics
  avg_jvm_gc_time_ms: number | null;
  avg_shuffle_read_bytes: number | null;
  avg_shuffle_write_bytes: number | null;
  avg_input_bytes: number | null;
  avg_output_bytes: number | null;
  avg_memory_bytes_spilled: number | null;
  avg_disk_bytes_spilled: number | null;
  avg_peak_execution_memory: number | null;
  // Peak (max) values across runs
  peak_driver_memory_used_mb: number | null;
  peak_executor_memory_mb: number | null;
  peak_cpu_utilization_pct: number | null;
  peak_executors_active: number | null;
  peak_execution_memory: number | null;
  metrics_source: string | null;
}

export interface CapacityBar {
  label: string;
  allocated: string;
  used: string;
  max_capacity: string;
  allocated_pct: number;
  used_pct: number;
}

export interface ResourceHistoryRecord {
  execution_date: string | null;
  dag_id: string;
  dag_run_id: string;
  status: string;
  duration_seconds: number | null;
  driver_memory_used_mb: number | null;
  executor_memory_peak_mb: number | null;
  cpu_utilization_pct: number | null;
  executors_active: number | null;
  peak_execution_memory: number | null;
  jvm_gc_time_ms: number | null;
  shuffle_read_bytes: number | null;
  shuffle_write_bytes: number | null;
  input_bytes: number | null;
  output_bytes: number | null;
  memory_bytes_spilled: number | null;
  disk_bytes_spilled: number | null;
  metrics_source: string | null;
}

export interface ResourceHistoryResponse {
  records: ResourceHistoryRecord[];
  total: number;
}

export interface ResourceMetrics {
  avg_duration_seconds: number | null;
  min_duration_seconds: number | null;
  max_duration_seconds: number | null;
  latest_duration_seconds: number | null;
  recent_runs: DurationRun[];
  run_count: number;
  success_rate: number | null;

  resource_configs: ResourceConfigEntry[];
  actual_usage: ActualUsage;
  capacity: CapacityBar[];
}
