import apiClient from "./client";
import type { DagNetworksResponse } from "@/types/dag-network";

export async function fetchDagNetworks(pipelineId: string): Promise<DagNetworksResponse> {
  const { data } = await apiClient.get<DagNetworksResponse>(`/pipelines/${pipelineId}/dags`);
  return data;
}
