import apiClient from "./client";
import type { DagSummaryResponse } from "@/types/dag-summary";

export async function fetchDagSummary(
  dateParams?: Record<string, string>,
): Promise<DagSummaryResponse> {
  const { data } = await apiClient.get<DagSummaryResponse>("/dags/summary", {
    params: dateParams,
  });
  return data;
}
