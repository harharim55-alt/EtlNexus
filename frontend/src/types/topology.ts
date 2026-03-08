export interface TopologyTask {
  task_id: string;
  pipeline_name: string | null;
  pipeline_id: string | null;
  status: string;
  dag_id: string;
}

export interface TopologyGraph {
  pipeline_task_id: string;
  pipeline_status: string;
  dag_ids: string[];
  upstream_needs: TopologyTask[];
  upstream_prefers: TopologyTask[];
  downstream: TopologyTask[];
}
