import apiClient from "./client";
import type { PipelineConsumersResponse } from "@/types/consumer";

export async function fetchPipelineConsumers(etlName: string): Promise<PipelineConsumersResponse> {
  const { data } = await apiClient.get<PipelineConsumersResponse>(
    `/consumers/${etlName}`,
  );
  return data;
}
