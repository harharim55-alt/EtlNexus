export interface TopologyTask {
  task_id: string;
  pipeline_name: string | null;
  pipeline_id: string | null;
  status: string;
  dag_id: string;
  task_group_id: string | null;
}

export interface TopologySensor {
  sensor_name: string;
  display_name: string;
  sensor_id: string | null;
  status: string | null;
  team: string | null;
  volume_per_day: number | null;
  dag_ids: string[];
}

export interface TopologyGraph {
  pipeline_task_id: string;
  pipeline_status: string;
  dag_ids: string[];
  upstream_sensors: TopologySensor[];
  upstream_needs: TopologyTask[];
  upstream_prefers: TopologyTask[];
  downstream: TopologyTask[];
}

export interface UpstreamNode {
  task_id: string;
  pipeline_name: string | null;
  pipeline_id: string | null;
  status: string;
  dag_id: string;
  task_group_id: string | null;
  depth: number;
  is_current: boolean;
  is_sensor: boolean;
  sensor_name: string | null;
}

export interface UpstreamEdge {
  source_task_id: string;
  target_task_id: string;
  edge_type: "needs" | "prefers";
}

export interface UpstreamTopologyGraph {
  pipeline_task_id: string;
  pipeline_status: string;
  dag_id: string | null;
  dag_ids: string[];
  nodes: UpstreamNode[];
  edges: UpstreamEdge[];
  sensors: TopologySensor[];
  max_depth: number;
}
