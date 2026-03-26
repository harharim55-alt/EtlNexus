import apiClient from "./client";
import type { ResourceMetrics, ResourceHistoryResponse } from "@/types/resources";
import type { PipelineRunsResponse, PipelineRunDetail } from "@/types/runs";

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

export async function fetchPipelineRuns(
  pipelineId: string,
  skip: number,
  limit: number,
): Promise<PipelineRunsResponse> {
  const { data } = await apiClient.get<PipelineRunsResponse>(
    `/pipelines/${pipelineId}/runs`,
    { params: { skip, limit } },
  );
  return data;
}

export async function fetchRunDetail(
  pipelineId: string,
  dagRunId: string,
): Promise<PipelineRunDetail> {
  const { data } = await apiClient.get<PipelineRunDetail>(
    `/pipelines/${pipelineId}/runs/${encodeURIComponent(dagRunId)}`,
  );
  return data;
}
