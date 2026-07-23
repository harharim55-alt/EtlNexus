import apiClient from "./client";
import type {
  PipelineListResponse,
  PipelineDetail,
  PipelineUpdateRequest,
  PipelineUpdateResponse,
  RevisionListResponse,
} from "@/types/pipeline";

export interface PipelineFilterParams {
  team?: string[];
  schedule?: string[];
}

export async function fetchPipelines(
  query?: string,
  skip = 0,
  limit = 50,
  dateParams?: Record<string, string>,
  filters?: PipelineFilterParams,
): Promise<PipelineListResponse> {
  const { data } = await apiClient.get<PipelineListResponse>("/data-products", {
    params: { q: query, skip, limit, ...dateParams, ...filters },
    paramsSerializer: {
      indexes: null, // serialize arrays as team=a&team=b (no bracket indices)
    },
  });
  return data;
}

export async function fetchPipelineDetail(productId: string): Promise<PipelineDetail> {
  const { data } = await apiClient.get<PipelineDetail>(`/data-products/${productId}`);
  return data;
}

export async function updatePipeline(
  productId: string,
  body: PipelineUpdateRequest,
): Promise<PipelineUpdateResponse> {
  const { data } = await apiClient.patch<PipelineUpdateResponse>(
    `/data-products/${productId}`,
    body,
  );
  return data;
}

export async function fetchRevisions(
  productId: string,
  field?: "description" | "documentation",
  skip = 0,
  limit = 50,
): Promise<RevisionListResponse> {
  const { data } = await apiClient.get<RevisionListResponse>(
    `/data-products/${productId}/revisions`,
    { params: { field, skip, limit } },
  );
  return data;
}

export async function restoreRevision(
  productId: string,
  revisionId: string,
): Promise<PipelineUpdateResponse> {
  const { data } = await apiClient.post<PipelineUpdateResponse>(
    `/data-products/${productId}/revisions/${revisionId}/restore`,
  );
  return data;
}
