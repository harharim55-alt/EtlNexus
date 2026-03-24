import apiClient from "./client";
import type { ResourceMetrics, ResourceHistoryResponse } from "@/types/resources";

export async function fetchResourceMetrics(
  pipelineId: string,
  dateParams?: Record<string, string>,
): Promise<ResourceMetrics> {
  const { data } = await apiClient.get<ResourceMetrics>(
    `/pipelines/${pipelineId}/resources`,
    { params: dateParams },
  );
  return data;
}

export async function fetchResourceHistory(
  pipelineId: string,
  dateParams?: Record<string, string>,
): Promise<ResourceHistoryResponse> {
  const { data } = await apiClient.get<ResourceHistoryResponse>(
    `/pipelines/${pipelineId}/resources/history`,
    { params: dateParams },
  );
  return data;
}
