import { useState, useEffect, type ReactNode } from "react";
import { AuthProvider as OidcAuthProvider } from "react-oidc-context";
import { fetchAuthConfig } from "@/api/auth";
import { useAuthStore } from "@/stores/auth-store";
import { useAIStore } from "@/stores/ai-store";
import { useAppConfigStore } from "@/stores/app-config-store";
import type { AuthConfig } from "@/types/auth";
import { Skeleton } from "@/components/ui/skeleton";
import { AuthGuard } from "./AuthGuard";

interface Props {
  children: ReactNode;
}

const DEFAULT_USER = {
  username: "admin",
  full_name: "Admin",
  email: "admin@localhost",
  role: "admin",
  is_master: true,
  teams: [],
};

/**
 * Top-level auth initialization component.
 *
 * Fetches `/api/auth/config` on mount to determine the SSO mode:
 * - **SSO enabled**: wraps children in `OidcAuthProvider` (react-oidc-context)
 *   so the SPA runs the OIDC authorization-code + PKCE flow against Keycloak
 *   (public client). `redirect_uri` is the SPA origin.
 * - **SSO disabled** (or config fetch fails): sets a default admin user in the
 *   auth store and renders children directly — no OIDC provider in the tree.
 *
 * Always wraps children in `AuthGuard`, which handles the OIDC login flow and
 * token syncing when SSO is active.
 */
export function AuthBootstrap({ children }: Props) {
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const setSsoEnabled = useAuthStore((s) => s.setSsoEnabled);
  const setUser = useAuthStore((s) => s.setUser);
  const setToken = useAuthStore((s) => s.setToken);

  useEffect(() => {
    let cancelled = false;

    async function loadConfig() {
      try {
        const config = await fetchAuthConfig();
        if (cancelled) return;

        setAuthConfig(config);
        setSsoEnabled(config.sso_enabled);
        if (config.ai_greeting) useAIStore.getState().setGreeting(config.ai_greeting);
        useAppConfigStore.getState().setBranding(config.app_name, config.app_owner);
        if (config.ai_request_timeout_seconds) {
          useAppConfigStore.getState().setAiRequestTimeoutMs(config.ai_request_timeout_seconds * 1000);
        }

        if (!config.sso_enabled) {
          // No SSO: set a default admin user so everything works
          setUser(DEFAULT_USER);
          setToken("no-sso");
        }
      } catch (err) {
        if (cancelled) return;
        // If auth config endpoint doesn't exist, treat as SSO disabled
        console.warn("Auth config fetch failed, assuming SSO disabled:", err);
        setSsoEnabled(false);
        setUser(DEFAULT_USER);
        setToken("no-sso");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadConfig();
    return () => {
      cancelled = true;
    };
  }, [setSsoEnabled, setUser, setToken]);

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Skeleton className="size-12 rounded-xl bg-hover-bg" />
          <Skeleton className="h-4 w-40 bg-hover-bg" />
          <p className="text-xs text-text-faint font-mono mt-2">
            Loading configuration...
          </p>
        </div>
      </div>
    );
  }

  // SSO enabled: wrap with OIDC provider (SPA does the OIDC flow; public client).
  if (authConfig?.sso_enabled) {
    const oidcConfig = {
      authority: authConfig.issuer_url,
      client_id: authConfig.client_id,
      // Trailing slash to match the SPA-root redirect URI registered in Keycloak
      // (e.g. http://localhost:5173/).
      redirect_uri: window.location.origin + "/",
      post_logout_redirect_uri: window.location.origin + "/",
      scope: "openid profile email",
      automaticSilentRenew: true,
      // Confidential client: oidc-client-ts sends this on the token exchange
      // (client_secret_post). Omitted for a public client.
      ...(authConfig.client_secret ? { client_secret: authConfig.client_secret } : {}),
      // Clean ?code/&state from the URL after the redirect callback.
      onSigninCallback: () => {
        window.history.replaceState({}, document.title, window.location.pathname);
      },
    };

    return (
      <OidcAuthProvider {...oidcConfig}>
        <AuthGuard>{children}</AuthGuard>
      </OidcAuthProvider>
    );
  }

  // SSO disabled: render children directly (default user already set)
  return <AuthGuard>{children}</AuthGuard>;
}
