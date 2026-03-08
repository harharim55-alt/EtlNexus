import apiClient from "./client";
import type { PipelineUsageResponse } from "@/types/usage";

export async function fetchPipelineUsage(pipelineId: string): Promise<PipelineUsageResponse> {
  const { data } = await apiClient.get<PipelineUsageResponse>(`/pipelines/${pipelineId}/usage`);
  return data;
}
