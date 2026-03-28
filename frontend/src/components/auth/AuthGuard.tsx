import { useEffect } from "react";
import { useAuth } from "react-oidc-context";
import { useAuthStore } from "@/stores/auth-store";
import { useCurrentUser } from "@/hooks/use-auth";
import { LoginPage } from "./LoginPage";
import { Skeleton } from "@/components/ui/skeleton";

interface AuthGuardProps {
  children: React.ReactNode;
}

/**
 * Route guard that gates children behind authentication.
 *
 * When SSO is disabled, renders children immediately (default user was already
 * set by `AuthBootstrap`). When SSO is enabled, delegates to `SSOGuard` which
 * manages the OIDC login flow, token syncing, and user info fetching.
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const ssoEnabled = useAuthStore((s) => s.ssoEnabled);

  if (!ssoEnabled) {
    // SSO disabled: already set up default user in AuthProvider
    return <>{children}</>;
  }

  return <SSOGuard>{children}</SSOGuard>;
}

/**
 * SSO-specific guard — must only render inside `OidcAuthProvider`.
 *
 * Handles: OIDC redirect callback cleanup (removes code/state query params),
 * token syncing to the Zustand auth store, and user info fetching via
 * `useCurrentUser`. Shows a loading skeleton while authenticating, or the
 * `LoginPage` if the user hasn't completed OIDC login yet.
 */
function SSOGuard({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const setToken = useAuthStore((s) => s.setToken);
  const setOidcSignout = useAuthStore((s) => s.setOidcSignout);
  const setOidcSigninSilent = useAuthStore((s) => s.setOidcSigninSilent);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { isLoading: isLoadingUser, isError: isUserError } = useCurrentUser();

  // Sync OIDC token to auth store
  useEffect(() => {
    if (auth.isAuthenticated && auth.user?.access_token) {
      setToken(auth.user.access_token);
    }
  }, [auth.isAuthenticated, auth.user?.access_token, setToken]);

  // Register OIDC signout callback so the 401 interceptor can trigger a real signout
  useEffect(() => {
    if (auth.isAuthenticated) {
      setOidcSignout(() => auth.removeUser());
    }
    return () => setOidcSignout(null);
  }, [auth.isAuthenticated, auth.removeUser, setOidcSignout]);

  // Register OIDC signinSilent callback for axios 401 token refresh
  useEffect(() => {
    if (auth.isAuthenticated) {
      setOidcSigninSilent(() => auth.signinSilent());
    }
    return () => setOidcSigninSilent(null);
  }, [auth.isAuthenticated, auth.signinSilent, setOidcSigninSilent]);

  // Handle OIDC callback (remove code/state from URL)
  useEffect(() => {
    if (auth.isAuthenticated) {
      const url = new URL(window.location.href);
      if (url.searchParams.has("code") || url.searchParams.has("state")) {
        url.searchParams.delete("code");
        url.searchParams.delete("state");
        url.searchParams.delete("session_state");
        window.history.replaceState({}, "", url.pathname);
      }
    }
  }, [auth.isAuthenticated]);

  // Loading states
  if (auth.isLoading) {
    return <AuthLoadingScreen />;
  }

  // Not authenticated with OIDC: show login
  if (!auth.isAuthenticated) {
    return <LoginPage />;
  }

  // Authenticated with OIDC but /me fetch failed after retries
  if (!isAuthenticated && isUserError) {
    return <AuthErrorScreen onRetry={() => window.location.reload()} />;
  }

  // Authenticated with OIDC but still fetching user info
  if (!isAuthenticated && isLoadingUser) {
    return <AuthLoadingScreen />;
  }

  return <>{children}</>;
}

function AuthLoadingScreen() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4">
        <Skeleton className="size-12 rounded-xl bg-hover-bg" />
        <Skeleton className="h-4 w-32 bg-hover-bg" />
        <p className="text-xs text-text-faint font-mono mt-2">
          Authenticating...
        </p>
      </div>
    </div>
  );
}

function AuthErrorScreen({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="size-12 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
          <span className="text-rose-400 text-lg">!</span>
        </div>
        <p className="text-sm text-text-secondary">Failed to load user profile</p>
        <button
          onClick={onRetry}
          className="text-xs text-indigo-400 hover:text-indigo-300 font-mono underline underline-offset-2"
        >
          Retry
        </button>
      </div>
    </div>
  );
}
