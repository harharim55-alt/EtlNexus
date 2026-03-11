import apiClient from "./client";
import type { TopologyGraph, UpstreamTopologyGraph } from "@/types/topology";

export async function fetchTopology(
  pipelineId: string,
  dagId?: string | null,
): Promise<TopologyGraph> {
  const params = dagId ? { dag_id: dagId } : {};
  const { data } = await apiClient.get<TopologyGraph>(
    `/pipelines/${pipelineId}/topology`,
    { params },
  );
  return data;
}

export async function fetchUpstreamTopology(
  pipelineId: string,
  dagId?: string | null,
): Promise<UpstreamTopologyGraph> {
  const params = dagId ? { dag_id: dagId } : {};
  const { data } = await apiClient.get<UpstreamTopologyGraph>(
    `/pipelines/${pipelineId}/topology/upstream`,
    { params },
  );
  return data;
}
