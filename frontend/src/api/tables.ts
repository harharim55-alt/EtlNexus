import apiClient from "./client";
import type { NamespaceListResponse, TableListResponse, TableSchema } from "@/types/table";

/** All catalog tables, optionally filtered server-side by team(s) + name. */
export async function fetchTables(teams?: string[], q?: string): Promise<TableListResponse> {
  const { data } = await apiClient.get<TableListResponse>("/tables", {
    params: { team: teams && teams.length ? teams : undefined, q: q || undefined },
    paramsSerializer: { indexes: null },
  });
  return data;
}

/** Read a single table's schema live from Spark Connect (on demand). */
export async function fetchTableSchema(namespace: string, table: string): Promise<TableSchema> {
  const { data } = await apiClient.get<TableSchema>("/tables/schema", {
    params: { namespace, table },
  });
  return data;
}

/** Distinct namespaces present in the catalog (for the team filter). */
export async function fetchNamespaces(): Promise<NamespaceListResponse> {
  const { data } = await apiClient.get<NamespaceListResponse>("/tables/namespaces");
  return data;
}
