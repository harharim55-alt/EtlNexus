import apiClient from "./client";
import type { PipelineUsageResponse } from "@/types/usage";

export async function fetchPipelineUsage(etlName: string): Promise<PipelineUsageResponse> {
  const { data } = await apiClient.get<PipelineUsageResponse>(
    `/usage/${etlName}`,
  );
  return data;
}
