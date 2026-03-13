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

export interface VisibilityGrant {
  id: string;
  grantee_team_id: string | null;
  grantee_team_name: string | null;
  grantee_user_id: string | null;
  grantee_user_name: string | null;
  grantee_user_email: string | null;
  pipeline_id: string | null;
  source_team_id: string | null;
  source_team_name: string | null;
  grant_level: string;
  granted_by: string;
  created_at: string;
}

export interface GrantListResponse {
  items: VisibilityGrant[];
  total: number;
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

export interface VisibilityGrantRequest {
  grantee_team_id?: string | null;
  grantee_user_id?: string | null;
  pipeline_id?: string | null;
  source_team_id?: string | null;
  grant_level?: string;
}
