import apiClient from "./client";
import type { PipelineLog } from "@/types/pipeline";

export interface LogListResponse {
  items: PipelineLog[];
}

export async function fetchPipelineLogs(pipelineId: string): Promise<LogListResponse> {
  const { data } = await apiClient.get<LogListResponse>(`/pipelines/${pipelineId}/logs`);
  return data;
}

export async function createPipelineLog(pipelineId: string, name: string, ordinalPosition = 0): Promise<PipelineLog> {
  const { data } = await apiClient.post<PipelineLog>(`/pipelines/${pipelineId}/logs`, {
    name,
    ordinal_position: ordinalPosition,
  });
  return data;
}

export async function updatePipelineLog(pipelineId: string, logId: string, body: { name?: string; ordinal_position?: number }): Promise<PipelineLog> {
  const { data } = await apiClient.patch<PipelineLog>(`/pipelines/${pipelineId}/logs/${logId}`, body);
  return data;
}

export async function deletePipelineLog(pipelineId: string, logId: string): Promise<void> {
  await apiClient.delete(`/pipelines/${pipelineId}/logs/${logId}`);
}

export async function setLogNetworks(
  pipelineId: string,
  logId: string,
  networks: { network_id: string; retention?: string }[],
): Promise<PipelineLog> {
  const { data } = await apiClient.put<PipelineLog>(`/pipelines/${pipelineId}/logs/${logId}/networks`, {
    networks,
  });
  return data;
}

export async function setLogFields(
  pipelineId: string,
  logId: string,
  fields: { name: string; data_type?: string; ordinal_position?: number }[],
): Promise<PipelineLog> {
  const { data } = await apiClient.put<PipelineLog>(`/pipelines/${pipelineId}/logs/${logId}/fields`, {
    fields,
  });
  return data;
}
