import apiClient from "./client";
import type { BouncerListResponse, BouncerTopologyResponse } from "@/types/bouncer";

export async function fetchBouncers(team?: string): Promise<BouncerListResponse> {
  const params = team ? { team } : {};
  const { data } = await apiClient.get<BouncerListResponse>("/bouncers", { params });
  return data;
}

export async function fetchBouncerTopology(
  bouncerNames: string[],
  mode: string = "union",
): Promise<BouncerTopologyResponse> {
  const params = new URLSearchParams();
  for (const name of bouncerNames) {
    params.append("bouncers", name);
  }
  params.append("mode", mode);
  const { data } = await apiClient.get<BouncerTopologyResponse>(
    `/bouncers/topology?${params.toString()}`,
  );
  return data;
}
