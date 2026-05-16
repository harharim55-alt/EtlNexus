import apiClient from "./client";
import type { Network } from "@/types/pipeline";

export interface NetworkListResponse {
  items: Network[];
}

export async function fetchNetworks(): Promise<NetworkListResponse> {
  const { data } = await apiClient.get<NetworkListResponse>("/networks");
  return data;
}

export async function createNetwork(name: string, description?: string): Promise<Network> {
  const { data } = await apiClient.post<Network>("/networks", { name, description });
  return data;
}

export async function updateNetwork(networkId: string, body: { name?: string; description?: string }): Promise<Network> {
  const { data } = await apiClient.patch<Network>(`/networks/${networkId}`, body);
  return data;
}

export async function deleteNetwork(networkId: string): Promise<void> {
  await apiClient.delete(`/networks/${networkId}`);
}
