export interface Bouncer {
  id: string;
  bouncer_name: string;
  display_name: string;
  description: string | null;
  team: string | null;
  volume_per_day: number | null;
  status: string | null;
  dag_ids: string[];
}

export interface BouncerListResponse {
  bouncers: Bouncer[];
  teams: string[];
}

export interface BouncerTopologyNode {
  task_id: string;
  pipeline_name: string | null;
  pipeline_id: string | null;
  status: string;
  dag_id: string;
  depends_on_bouncers: string[];
}

export interface BouncerTopologyResponse {
  selected_bouncers: string[];
  downstream_etls: BouncerTopologyNode[];
  total_etl_count: number;
}
