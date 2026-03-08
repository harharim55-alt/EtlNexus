export interface PipelineConsumer {
  pipeline_id: string;
  pipeline_name: string;
  dag_id: string;
  airflow_status: string;
  last_run_at: string | null;
}

export interface PipelineConsumersResponse {
  consumers: PipelineConsumer[];
}
