import apiClient from "./client";
import type {
  PipelineListItem,
  PipelineDetail,
  JoinSuggestionsResponse,
  PipelineUpdateRequest,
  PipelineUpdateResponse,
} from "@/types/pipeline";

export async function fetchPipelines(query?: string): Promise<PipelineListItem[]> {
  const params = query ? { q: query } : {};
  const { data } = await apiClient.get<PipelineListItem[]>("/pipelines", { params });
  return data;
}

export async function fetchPipelineDetail(pipelineId: string): Promise<PipelineDetail> {
  const { data } = await apiClient.get<PipelineDetail>(`/pipelines/${pipelineId}`);
  return data;
}

export async function fetchJoinSuggestions(pipelineId: string): Promise<JoinSuggestionsResponse> {
  const { data } = await apiClient.get<JoinSuggestionsResponse>(`/pipelines/${pipelineId}/joins`);
  return data;
}

export interface SyncResponse {
  synced: boolean;
  pipeline_name: string;
}

export async function syncPipeline(pipelineId: string): Promise<SyncResponse> {
  const { data } = await apiClient.post<SyncResponse>(`/pipelines/${pipelineId}/sync`);
  return data;
}

export async function updatePipeline(
  pipelineId: string,
  body: PipelineUpdateRequest,
): Promise<PipelineUpdateResponse> {
  const { data } = await apiClient.patch<PipelineUpdateResponse>(
    `/pipelines/${pipelineId}`,
    body,
  );
  return data;
}
