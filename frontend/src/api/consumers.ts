import apiClient from "./client";
import type { PipelineConsumersResponse } from "@/types/consumer";

export async function fetchPipelineConsumers(pipelineId: string): Promise<PipelineConsumersResponse> {
  const { data } = await apiClient.get<PipelineConsumersResponse>(`/pipelines/${pipelineId}/consumers`);
  return data;
}
