import apiClient from "./client";
import type { TableListResponse } from "@/types/table";

export async function fetchTables(team?: string, q?: string): Promise<TableListResponse> {
  const { data } = await apiClient.get<TableListResponse>("/tables", {
    params: { team: team || undefined, q: q || undefined },
  });
  return data;
}
