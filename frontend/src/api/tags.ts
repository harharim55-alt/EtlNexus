import apiClient from "./client";
import type { Tag } from "@/types/pipeline";

export interface TagListResponse {
  items: Tag[];
}

export async function fetchTags(teamId?: string): Promise<TagListResponse> {
  const { data } = await apiClient.get<TagListResponse>("/tags", {
    params: teamId ? { team_id: teamId } : undefined,
  });
  return data;
}

export async function createTag(name: string): Promise<Tag> {
  const { data } = await apiClient.post<Tag>("/tags", { name });
  return data;
}

export async function deleteTag(tagId: string): Promise<void> {
  await apiClient.delete(`/tags/${tagId}`);
}

export async function setPipelineTags(pipelineId: string, tagIds: string[]): Promise<TagListResponse> {
  const { data } = await apiClient.put<TagListResponse>(`/pipelines/${pipelineId}/tags`, {
    tag_ids: tagIds,
  });
  return data;
}
