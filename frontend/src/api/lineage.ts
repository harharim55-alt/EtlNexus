import apiClient from "./client";
import type { LineageGraph } from "@/types/lineage";

export async function fetchLineage(pipelineId: string): Promise<LineageGraph> {
  const { data } = await apiClient.get<LineageGraph>(`/pipelines/${pipelineId}/lineage`);
  return data;
}
