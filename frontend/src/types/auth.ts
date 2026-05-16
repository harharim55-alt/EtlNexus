export interface AuthConfig {
  sso_enabled: boolean;
  issuer_url: string;
  client_id: string;
  audience: string;
}

export interface TeamMembership {
  id: string;
  name: string;
  role_in_team: string;
}

export interface UserInfo {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  is_beta: boolean;
  teams: TeamMembership[];
}
