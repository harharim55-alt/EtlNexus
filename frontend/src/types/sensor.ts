export interface Sensor {
  id: string;
  sensor_name: string;
  display_name: string;
  description: string | null;
  team: string | null;
  volume_per_day: number | null;
  status: string | null;
  dag_ids: string[];
}

export interface SensorListResponse {
  sensors: Sensor[];
  teams: string[];
}

export interface SensorTopologyNode {
  task_id: string;
  pipeline_name: string | null;
  pipeline_id: string | null;
  status: string;
  dag_id: string;
  depends_on_sensors: string[];
}

export interface SensorTopologyResponse {
  selected_sensors: string[];
  downstream_etls: SensorTopologyNode[];
  total_etl_count: number;
}
