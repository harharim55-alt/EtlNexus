import apiClient from "./client";
import type { ResourceMetrics } from "@/types/resources";

export async function fetchResourceMetrics(
  pipelineId: string,
): Promise<ResourceMetrics> {
  const { data } = await apiClient.get<ResourceMetrics>(
    `/pipelines/${pipelineId}/resources`,
  );
  return data;
}
