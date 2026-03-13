import apiClient from "./client";
import type {
  AdminTeam,
  TeamDetail,
  UserListResponse,
  GrantListResponse,
  VisibilityGrant,
  VisibilityGrantRequest,
} from "@/types/admin";

export async function fetchUsers(
  skip = 0,
  limit = 100,
): Promise<UserListResponse> {
  const { data } = await apiClient.get<UserListResponse>("/users", {
    params: { skip, limit },
  });
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

export async function fetchGrants(
  skip = 0,
  limit = 100,
): Promise<GrantListResponse> {
  const { data } = await apiClient.get<GrantListResponse>(
    "/visibility/grants",
    { params: { skip, limit } },
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
