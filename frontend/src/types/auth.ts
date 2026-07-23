export interface AuthConfig {
  sso_enabled: boolean;
  issuer_url: string;
  client_id: string;
  // Only set for a confidential client; oidc-client-ts sends it on the token exchange.
  client_secret?: string;
  audience: string;
  ai_greeting?: string;
  app_name?: string;
  app_owner?: string;
  ai_request_timeout_seconds?: number;
}

export interface UserInfo {
  username: string;
  // Human name (first + last) from SSO claims; falls back to username.
  full_name?: string;
  email: string;
  role: string;
  is_master: boolean;
  // Team names from Keycloak (no per-team role / id — teams are not persisted).
  teams: string[];
}
