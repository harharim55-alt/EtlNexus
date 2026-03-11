import apiClient from "./client";
import type { AuthConfig, UserInfo } from "@/types/auth";

export async function fetchAuthConfig(): Promise<AuthConfig> {
  const { data } = await apiClient.get<AuthConfig>("/auth/config");
  return data;
}

export async function fetchMe(token: string): Promise<UserInfo> {
  const { data } = await apiClient.get<UserInfo>("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data;
}
