export interface AirflowStatus {
  pipeline_id: string;
  dag_id: string;
  status: string;
  execution_date: string | null;
  last_checked_at: string | null;
}

export interface AirflowStatusesResponse {
  statuses: AirflowStatus[];
  airflow_connected: boolean;
}
