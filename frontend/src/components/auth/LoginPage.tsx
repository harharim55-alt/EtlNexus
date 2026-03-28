import { LogIn, Shield } from "lucide-react";
import { useAuth } from "react-oidc-context";

export function LoginPage() {
  const auth = useAuth();

  return (
    <div className="flex h-screen w-full items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-8">
        {/* Logo + branding */}
        <div className="flex flex-col items-center gap-4">
          <div className="size-16 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl flex items-center justify-center">
            <Shield className="size-8 text-indigo-400" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold text-foreground tracking-tight">
              ETL Nexus
            </h1>
            <p className="text-sm text-text-muted mt-1">
              Data Architecture Command Center
            </p>
          </div>
        </div>

        {/* Sign-in card */}
        <div className="w-80 bg-card border border-border rounded-2xl p-8 flex flex-col items-center gap-6">
          <p className="text-sm text-text-secondary text-center">
            Sign in with your organization account to continue
          </p>

          <button
            onClick={() => auth.signinRedirect()}
            disabled={auth.isLoading}
            className="w-full flex items-center justify-center gap-2.5 px-5 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition-colors shadow-lg shadow-indigo-500/20"
          >
            <LogIn className="size-4" />
            {auth.isLoading ? "Redirecting..." : "Sign in with SSO"}
          </button>

          {auth.error && (
            <p className="text-xs text-red-400/80 text-center font-mono bg-red-500/5 border border-red-500/10 rounded-lg px-3 py-2 w-full">
              {auth.error.message}
            </p>
          )}
        </div>

        <p className="text-[10px] text-text-faint font-mono">
          Secure authentication via OpenID Connect
        </p>
      </div>
    </div>
  );
}
