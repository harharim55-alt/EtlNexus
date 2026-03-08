import apiClient from "./client";
import type { AirflowStatusesResponse } from "@/types/airflow";

export async function fetchAllAirflowStatuses(): Promise<AirflowStatusesResponse> {
  const { data } = await apiClient.get<AirflowStatusesResponse>("/airflow/status");
  return data;
}
