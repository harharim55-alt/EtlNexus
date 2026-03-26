import apiClient from "./client";
import type { AirflowStatusesResponse } from "@/types/airflow";

export async function fetchAllAirflowStatuses(): Promise<AirflowStatusesResponse> {
  const { data } = await apiClient.get<AirflowStatusesResponse>("/airflow/status");
  return data;
}

export async function syncAllPipelines(): Promise<{ synced: number; message: string }> {
  const { data } = await apiClient.post<{ synced: number; message: string }>("/airflow/sync-all");
  return data;
}
