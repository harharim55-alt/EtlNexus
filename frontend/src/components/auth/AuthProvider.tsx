import { useState, useEffect, type ReactNode } from "react";
import { AuthProvider as OidcAuthProvider } from "react-oidc-context";
import { fetchAuthConfig } from "@/api/auth";
import { useAuthStore } from "@/stores/auth-store";
import type { AuthConfig } from "@/types/auth";
import { Skeleton } from "@/components/ui/skeleton";
import { AuthGuard } from "./AuthGuard";

interface Props {
  children: ReactNode;
}

const DEFAULT_USER = {
  id: "local-admin",
  email: "admin@localhost",
  display_name: "Local Admin",
  role: "admin",
  is_active: true,
  is_beta: true,
  teams: [],
};

/**
 * Top-level auth initialization component.
 *
 * Fetches `/api/auth/config` on mount to determine the SSO mode:
 * - **SSO enabled**: wraps children in `OidcAuthProvider` (react-oidc-context)
 *   so that downstream components can call `useAuth()`.
 * - **SSO disabled** (or config fetch fails): sets a default admin user in the
 *   auth store and renders children directly — no OIDC provider in the tree.
 *
 * Always wraps children in `AuthGuard`, which handles OIDC redirect flow and
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

  // SSO enabled: wrap with OIDC provider
  if (authConfig?.sso_enabled) {
    const oidcConfig = {
      authority: authConfig.issuer_url,
      client_id: authConfig.client_id,
      redirect_uri: window.location.origin,
      post_logout_redirect_uri: window.location.origin,
      scope: "openid profile email",
      automaticSilentRenew: true,
      ...(authConfig.audience
        ? { extraQueryParams: { audience: authConfig.audience } }
        : {}),
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
