export interface DagTaskSummary {
  task_id: string;
  pipeline_name: string | null;
  pipeline_id: string | null;
  status: string;
  latest_duration_seconds: number | null;
  avg_duration_seconds: number | null;
  task_group_id: string | null;
}

export interface DagSummary {
  dag_id: string;
  description: string | null;
  schedule_interval: string | null;
  is_paused: boolean;
  task_count: number;
  pipeline_count: number;
  total_duration_seconds: number | null;
  avg_task_duration_seconds: number | null;
  min_task_duration_seconds: number | null;
  max_task_duration_seconds: number | null;
  status_counts: Record<string, number>;
  success_rate: number | null;
  latest_run_start: string | null;
  latest_run_end: string | null;
  typical_finish_hour: string | null;
  total_runs_30d: number;
  dag_success_rate_30d: number | null;
  tasks: DagTaskSummary[];
}

export interface DagSummaryAggregate {
  total_dags: number;
  total_pipelines: number;
  active_dags: number;
  overall_success_rate: number | null;
  total_runs_30d: number;
}

export interface DagSummaryResponse {
  aggregate: DagSummaryAggregate;
  dags: DagSummary[];
}
