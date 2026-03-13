import apiClient from "./client";
import type {
  PipelineListResponse,
  PipelineDetail,
  JoinSuggestionsResponse,
  PipelineUpdateRequest,
  PipelineUpdateResponse,
  RevisionListResponse,
} from "@/types/pipeline";

export async function fetchPipelines(
  query?: string,
  skip = 0,
  limit = 50,
  dateParams?: Record<string, string>,
): Promise<PipelineListResponse> {
  const { data } = await apiClient.get<PipelineListResponse>("/pipelines", {
    params: { q: query, skip, limit, ...dateParams },
  });
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

export async function fetchRevisions(
  pipelineId: string,
  field?: "description" | "documentation",
  skip = 0,
  limit = 50,
): Promise<RevisionListResponse> {
  const { data } = await apiClient.get<RevisionListResponse>(
    `/pipelines/${pipelineId}/revisions`,
    { params: { field, skip, limit } },
  );
  return data;
}

export async function restoreRevision(
  pipelineId: string,
  revisionId: string,
): Promise<PipelineUpdateResponse> {
  const { data } = await apiClient.post<PipelineUpdateResponse>(
    `/pipelines/${pipelineId}/revisions/${revisionId}/restore`,
  );
  return data;
}
