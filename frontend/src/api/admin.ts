import apiClient from "./client";
import type {
  AdminTeam,
  TeamDetail,
  TeamMember,
  UserListResponse,
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

export async function updateUserActive(
  userId: string,
  isActive: boolean,
): Promise<{ ok: boolean }> {
  const { data } = await apiClient.patch<{ ok: boolean }>(
    `/users/${userId}/active`,
    { is_active: isActive },
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

export async function addTeamMember(
  teamId: string,
  username: string,
): Promise<TeamMember> {
  const { data } = await apiClient.post<TeamMember>(
    `/teams/${teamId}/members`,
    { username },
  );
  return data;
}

export async function removeTeamMember(
  teamId: string,
  userId: string,
): Promise<{ ok: boolean }> {
  const { data } = await apiClient.delete<{ ok: boolean }>(
    `/teams/${teamId}/members/${userId}`,
  );
  return data;
}
