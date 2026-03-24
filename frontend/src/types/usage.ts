export interface PipelineUsage {
  id: string;
  consumer_name: string;
  usage_type: string;
  description: string | null;
  last_accessed_at: string | null;
  unique_reads: number;
  total_reads: number;
  airflow_status: string | null;
  dag_id: string | null;
  is_current: boolean;
}

export interface PipelineUsageResponse {
  usages: PipelineUsage[];
}
