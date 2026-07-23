import { LogIn } from "lucide-react";
import { useAuth } from "react-oidc-context";
import { useAppConfigStore } from "@/stores/app-config-store";

export function LoginPage() {
  const auth = useAuth();
  // Branding from the backend (APP_NAME / APP_OWNER) via /api/auth/config.
  const appName = useAppConfigStore((s) => s.appName);
  const appOwner = useAppConfigStore((s) => s.appOwner);

  return (
    <div className="relative flex h-screen w-full items-center justify-center overflow-hidden bg-background">
      {/* Animated aurora background */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="login-blob login-blob-1" />
        <div className="login-blob login-blob-2" />
        <div className="login-blob login-blob-3" />
      </div>

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center gap-8 px-6">
        {/* Logo + branding */}
        <div className="flex flex-col items-center gap-5">
          <div className="login-logo relative">
            <div className="absolute inset-0 -z-10 rounded-3xl bg-indigo-500/30 blur-2xl" />
            <img
              src="/logo.svg"
              alt={appName}
              className="size-20 drop-shadow-[0_0_25px_rgba(99,102,241,0.55)]"
            />
          </div>
          <div className="text-center">
            <h1 className="bg-gradient-to-r from-white via-indigo-100 to-indigo-300 bg-clip-text text-4xl font-bold tracking-tight text-transparent">
              {appName}
            </h1>
            <p className="mt-2 text-sm tracking-wide text-text-muted">
              Data Architecture Command Center
            </p>
          </div>
        </div>

        {/* Sign-in card (glass) */}
        <div className="flex w-80 flex-col items-center gap-6 rounded-2xl border border-white/10 bg-white/5 p-8 shadow-2xl backdrop-blur-xl">
          <p className="text-center text-sm text-text-secondary">
            Sign in with your organization account to continue
          </p>

          <button
            onClick={() => auth.signinRedirect()}
            disabled={auth.isLoading}
            className="flex w-full items-center justify-center gap-2.5 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-medium text-white shadow-lg shadow-indigo-500/20 transition-all duration-200 hover:bg-indigo-500 hover:shadow-indigo-500/50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <LogIn className="size-4" />
            {auth.isLoading ? "Redirecting..." : "Sign in with SSO"}
          </button>

          {auth.error && (
            <p className="w-full rounded-lg border border-red-500/10 bg-red-500/5 px-3 py-2 text-center font-mono text-xs text-red-400/80">
              {auth.error.message}
            </p>
          )}
        </div>

        <p className="text-[10px] font-mono text-text-faint">
          Secure authentication via OpenID Connect
        </p>

        {appOwner && (
          <p className="text-[10px] font-mono uppercase tracking-widest text-text-faint">
            Made by {appOwner}
          </p>
        )}
      </div>

      <style>{`
        @keyframes login-float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
        @keyframes login-drift-1 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(40px,30px) scale(1.12); } }
        @keyframes login-drift-2 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(-32px,22px) scale(1.16); } }
        @keyframes login-drift-3 { 0%,100% { transform: translate(-50%,-50%) scale(1); } 50% { transform: translate(-46%,-56%) scale(1.08); } }
        .login-logo { animation: login-float 4.5s ease-in-out infinite; }
        .login-blob { position: absolute; border-radius: 9999px; filter: blur(80px); }
        .login-blob-1 { width: 440px; height: 440px; background: rgba(99,102,241,0.38); top: -90px; left: -70px; animation: login-drift-1 15s ease-in-out infinite; }
        .login-blob-2 { width: 400px; height: 400px; background: rgba(139,92,246,0.32); bottom: -110px; right: -50px; animation: login-drift-2 17s ease-in-out infinite; }
        .login-blob-3 { width: 320px; height: 320px; background: rgba(59,130,246,0.26); top: 45%; left: 50%; transform: translate(-50%,-50%); animation: login-drift-3 19s ease-in-out infinite; }
        @media (prefers-reduced-motion: reduce) {
          .login-logo, .login-blob { animation: none; }
        }
      `}</style>
    </div>
  );
}
