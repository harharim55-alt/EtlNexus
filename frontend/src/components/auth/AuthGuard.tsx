import { useEffect } from "react";
import { useAuth } from "react-oidc-context";
import { useAuthStore } from "@/stores/auth-store";
import { useCurrentUser } from "@/hooks/use-auth";
import { LoginPage } from "./LoginPage";
import { Skeleton } from "@/components/ui/skeleton";

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const ssoEnabled = useAuthStore((s) => s.ssoEnabled);

  if (!ssoEnabled) {
    // SSO disabled: already set up default user in AuthProvider
    return <>{children}</>;
  }

  return <SSOGuard>{children}</SSOGuard>;
}

function SSOGuard({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const setToken = useAuthStore((s) => s.setToken);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { isLoading: isLoadingUser } = useCurrentUser();

  // Sync OIDC token to auth store
  useEffect(() => {
    if (auth.isAuthenticated && auth.user?.access_token) {
      setToken(auth.user.access_token);
    }
  }, [auth.isAuthenticated, auth.user?.access_token, setToken]);

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

  // Authenticated with OIDC but still fetching user info
  if (!isAuthenticated && isLoadingUser) {
    return <AuthLoadingScreen />;
  }

  return <>{children}</>;
}

function AuthLoadingScreen() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-[#09090b]">
      <div className="flex flex-col items-center gap-4">
        <Skeleton className="size-12 rounded-xl bg-white/5" />
        <Skeleton className="h-4 w-32 bg-white/5" />
        <p className="text-xs text-slate-600 font-mono mt-2">
          Authenticating...
        </p>
      </div>
    </div>
  );
}
