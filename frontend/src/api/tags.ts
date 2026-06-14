import apiClient from "./client";
import type { Tag, PipelineListItem } from "@/types/pipeline";

export interface TagListResponse {
  items: Tag[];
}

/** All tag-products (for the tag picker). */
export async function fetchTags(): Promise<TagListResponse> {
  const { data } = await apiClient.get<TagListResponse>("/tags");
  return data;
}

/** Tags applied to a product. */
export async function fetchProductTags(productId: string): Promise<TagListResponse> {
  const { data } = await apiClient.get<TagListResponse>(`/pipelines/${productId}/tags`);
  return data;
}

/** Replace the tags applied to a product. */
export async function setPipelineTags(pipelineId: string, tagIds: string[]): Promise<TagListResponse> {
  const { data } = await apiClient.put<TagListResponse>(`/pipelines/${pipelineId}/tags`, {
    tag_ids: tagIds,
  });
  return data;
}

/** Products tagged with a given tag (the tag detail page's sub-product tabs). */
export async function fetchTagMembers(tagId: string): Promise<PipelineListItem[]> {
  const { data } = await apiClient.get<PipelineListItem[]>(`/pipelines/${tagId}/members`);
  return data;
}
