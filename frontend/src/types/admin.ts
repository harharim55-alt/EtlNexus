import type { UserInfo } from "./auth";

/** Same shape as UserInfo — single source of truth for user data. */
export type AdminUser = UserInfo;

export interface UserListResponse {
  items: AdminUser[];
  total: number;
}

export interface AdminTeam {
  id: string;
  name: string;
  description: string | null;
  source: string;
  member_count: number;
}

export interface TeamMember {
  id: string;
  email: string;
  display_name: string;
  role: string;
  role_in_team: string;
}

export interface TeamDetail {
  id: string;
  name: string;
  description: string | null;
  source: string;
  members: TeamMember[];
}
