import apiClient from "./client";
import type { AIChatRequest, AIChatResponse } from "@/types/ai";

export async function sendAIMessage(request: AIChatRequest): Promise<AIChatResponse> {
  const { data } = await apiClient.post<AIChatResponse>("/ai/chat", request);
  return data;
}

export async function fetchJoinInsight(pipelineId: string): Promise<{ insight: string }> {
  const { data } = await apiClient.get<{ insight: string }>(`/pipelines/${pipelineId}/joins/ai`);
  return data;
}
