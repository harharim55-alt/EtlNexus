export interface PipelineUsage {
  id: string;
  consumer_name: string;
  usage_type: string;
  description: string | null;
  last_accessed_at: string | null;
  access_count: number;
  airflow_status: string | null;
}

export interface PipelineUsageResponse {
  usages: PipelineUsage[];
}
