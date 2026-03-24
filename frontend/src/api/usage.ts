import apiClient from "./client";
import type { PipelineUsageResponse } from "@/types/usage";

export async function fetchPipelineUsage(
  etlName: string,
  dateParams?: Record<string, string>,
  network?: string | null,
): Promise<PipelineUsageResponse> {
  const params: Record<string, string> = { ...dateParams };
  if (network) params.network = network;
  const { data } = await apiClient.get<PipelineUsageResponse>(
    `/usage/${etlName}`,
    { params },
  );
  return data;
}
