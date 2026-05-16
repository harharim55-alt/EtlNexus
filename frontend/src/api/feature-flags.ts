import apiClient from "./client";
import type { FeatureFlag } from "@/types/pipeline";

export interface FeatureFlagListResponse {
  items: FeatureFlag[];
}

export interface FeatureFlagCheckResponse {
  name: string;
  accessible: boolean;
}

export async function fetchFeatureFlags(): Promise<FeatureFlagListResponse> {
  const { data } = await apiClient.get<FeatureFlagListResponse>("/feature-flags");
  return data;
}

export async function checkFeatureFlag(flagName: string): Promise<FeatureFlagCheckResponse> {
  const { data } = await apiClient.get<FeatureFlagCheckResponse>(`/feature-flags/check/${flagName}`);
  return data;
}

export async function updateFeatureFlag(flagId: string, body: { enabled?: boolean; beta_only?: boolean }): Promise<FeatureFlag> {
  const { data } = await apiClient.put<FeatureFlag>(`/feature-flags/${flagId}`, body);
  return data;
}
