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
}

export interface ActualUsage {
  avg_driver_memory_used_mb: number | null;
  avg_executor_memory_peak_mb: number | null;
  avg_cpu_utilization_pct: number | null;
  avg_executors_active: number | null;
}

export interface CapacityBar {
  label: string;
  allocated: string;
  used: string;
  max_capacity: string;
  allocated_pct: number;
  used_pct: number;
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
