import apiClient from "./client";
import type { DagSummaryResponse } from "@/types/dag-summary";

export async function fetchDagSummary(): Promise<DagSummaryResponse> {
  const { data } = await apiClient.get<DagSummaryResponse>("/dags/summary");
  return data;
}
