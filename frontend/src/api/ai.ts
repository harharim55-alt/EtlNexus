import apiClient from "./client";
import { useAppConfigStore } from "@/stores/app-config-store";
import type { AIChatRequest, AIChatResponse } from "@/types/ai";

export async function sendAIMessage(request: AIChatRequest): Promise<AIChatResponse> {
  // The AI reply is a single long-blocking response (the backend buffers the whole
  // LLM stream), so it needs a far longer timeout than the default 30s client cap —
  // otherwise axios aborts mid-flight and the proxy logs a 499. Sourced at runtime
  // from /api/auth/config (AI_REQUEST_TIMEOUT_SECONDS).
  const timeout = useAppConfigStore.getState().aiRequestTimeoutMs;
  const { data } = await apiClient.post<AIChatResponse>("/ai/chat", request, { timeout });
  return data;
}
