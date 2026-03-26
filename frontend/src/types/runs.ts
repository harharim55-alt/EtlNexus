export interface PipelineRunItem {
  dag_run_id: string;
  dag_id: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  duration_seconds: number | null;
  has_execution_plan: boolean;
}

export interface PipelineRunsResponse {
  items: PipelineRunItem[];
  total: number;
}

export interface FieldSnapshot {
  name: string;
  data_type: string | null;
  ordinal_position: number;
}

export interface PipelineRunDetail {
  dag_run_id: string;
  dag_id: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
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
  spark_application_id: string | null;
  has_execution_plan: boolean;
  fields_snapshot: FieldSnapshot[] | null;
  source_tables_snapshot: string[] | null;
  destination_tables_snapshot: string[] | null;
}
