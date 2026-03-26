import apiClient from "./client";
import type { TopologyGraph, UpstreamTopologyGraph } from "@/types/topology";

export async function fetchTopology(
  pipelineId: string,
  dagId?: string | null,
  dagRunId?: string | null,
): Promise<TopologyGraph> {
  const params: Record<string, string> = {};
  if (dagId) params.dag_id = dagId;
  if (dagRunId) params.dag_run_id = dagRunId;
  const { data } = await apiClient.get<TopologyGraph>(
    `/pipelines/${pipelineId}/topology`,
    { params },
  );
  return data;
}

export async function fetchUpstreamTopology(
  pipelineId: string,
  dagId?: string | null,
  dagRunId?: string | null,
): Promise<UpstreamTopologyGraph> {
  const params: Record<string, string> = {};
  if (dagId) params.dag_id = dagId;
  if (dagRunId) params.dag_run_id = dagRunId;
  const { data } = await apiClient.get<UpstreamTopologyGraph>(
    `/pipelines/${pipelineId}/topology/upstream`,
    { params },
  );
  return data;
}
