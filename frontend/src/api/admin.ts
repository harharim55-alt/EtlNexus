import apiClient from "./client";
import type {
  AdminUser,
  AdminTeam,
  TeamDetail,
  VisibilityGrant,
  VisibilityGrantRequest,
} from "@/types/admin";

export async function fetchUsers(): Promise<AdminUser[]> {
  const { data } = await apiClient.get<AdminUser[]>("/users");
  return data;
}

export async function updateUserRole(
  userId: string,
  role: string,
): Promise<{ ok: boolean }> {
  const { data } = await apiClient.patch<{ ok: boolean }>(
    `/users/${userId}/role`,
    { role },
  );
  return data;
}

export async function fetchTeams(): Promise<AdminTeam[]> {
  const { data } = await apiClient.get<AdminTeam[]>("/teams");
  return data;
}

export async function fetchTeamDetail(teamId: string): Promise<TeamDetail> {
  const { data } = await apiClient.get<TeamDetail>(`/teams/${teamId}`);
  return data;
}

export async function fetchGrants(): Promise<VisibilityGrant[]> {
  const { data } = await apiClient.get<VisibilityGrant[]>(
    "/visibility/grants",
  );
  return data;
}

export async function createGrant(
  body: VisibilityGrantRequest,
): Promise<VisibilityGrant> {
  const { data } = await apiClient.post<VisibilityGrant>(
    "/visibility/grants",
    body,
  );
  return data;
}

export async function deleteGrant(grantId: string): Promise<{ ok: boolean }> {
  const { data } = await apiClient.delete<{ ok: boolean }>(
    `/visibility/grants/${grantId}`,
  );
  return data;
}
