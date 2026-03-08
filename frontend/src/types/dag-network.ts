export interface DagNetwork {
  network_name: string;
  last_synced_at: string | null;
}

export interface DagNetworksResponse {
  pipeline_id: string;
  networks: DagNetwork[];
}
