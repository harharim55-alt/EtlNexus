import { BarChart3, Database, HelpCircle, LogOut, Moon, Network, Package, Palette, Radio, Shield, Sparkles, Sun } from "lucide-react";
import { useNavigationStore } from "@/stores/navigation-store";
import { useAuthStore } from "@/stores/auth-store";
import { useFeatureFlagCheck } from "@/hooks/use-feature-flags";
import { useOnboardingStore } from "@/stores/onboarding-store";
import { isAdmin } from "@/lib/permissions";
import { useThemeStore } from "@/stores/theme-store";
import { useAuth } from "react-oidc-context";
import { NavIcon } from "./NavIcon";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { UserInitials } from "@/components/shared/UserInitials";

/** Only rendered when ssoEnabled=true, which guarantees OidcAuthProvider context. */
function SsoLogoutButton() {
  const auth = useAuth();
  const clearStore = useAuthStore((s) => s.logout);

  const handleLogout = () => {
    clearStore();
    auth.signoutRedirect();
  };

  return (
    <Tooltip>
      <TooltipTrigger
        className="p-1.5 text-text-faint hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all duration-200 cursor-pointer"
        onClick={handleLogout}
      >
        <LogOut className="size-4" />
      </TooltipTrigger>
      <TooltipContent
        side="right"
        className="bg-card border-border-prominent text-foreground text-xs font-medium"
      >
        Sign out
      </TooltipContent>
    </Tooltip>
  );
}

export function Sidebar() {
  const { activeTab, setActiveTab } = useNavigationStore();
  const user = useAuthStore((s) => s.user);
  const ssoEnabled = useAuthStore((s) => s.ssoEnabled);
  const { data: dagFlag } = useFeatureFlagCheck("dag_dashboard");
  const { data: bouncerFlag } = useFeatureFlagCheck("bouncer_dashboard");
  const showDags = isAdmin(user) || dagFlag?.accessible;
  const showBouncers = isAdmin(user) || bouncerFlag?.accessible;
  const theme = useThemeStore((s) => s.theme);
  const cycleTheme = useThemeStore((s) => s.cycleTheme);

  const themeIcon = theme === "dark" ? <Moon className="size-4" /> : theme === "light" ? <Sun className="size-4" /> : <Palette className="size-4" />;
  const themeLabel = theme === "dark" ? "Dark theme" : theme === "light" ? "Light theme" : "Pink theme";

  return (
    <nav className="w-20 border-r border-border bg-background flex flex-col items-center py-6 z-20 shrink-0">
      {/* Logo */}
      <div className="mb-8">
        <img src="/logo.svg" alt="ETL Nexus" className="w-11 h-11" />
      </div>

      {/* Nav Icons */}
      <div className="flex-1 flex flex-col gap-4 w-full px-3">
        <div data-nav-id="catalog">
          <NavIcon
            active={activeTab === "catalog"}
            onClick={() => setActiveTab("catalog")}
            icon={<Database className="w-5 h-5" />}
            tooltip="ETL Catalog"
          />
        </div>
        <div data-nav-id="data-products">
          <NavIcon
            active={activeTab === "data-products"}
            onClick={() => setActiveTab("data-products")}
            icon={<Package className="w-5 h-5" />}
            tooltip="Data Products"
          />
        </div>
        <div data-nav-id="matrix">
          <NavIcon
            active={activeTab === "matrix"}
            onClick={() => setActiveTab("matrix")}
            icon={<Network className="w-5 h-5" />}
            tooltip="Field Matrix"
          />
        </div>
        {showDags && (
          <div data-nav-id="dags">
            <NavIcon
              active={activeTab === "dags"}
              onClick={() => setActiveTab("dags")}
              icon={<BarChart3 className="w-5 h-5" />}
              tooltip="DAG Summary"
            />
          </div>
        )}
        {showBouncers && (
          <div data-nav-id="bouncers">
            <NavIcon
              active={activeTab === "bouncers"}
              onClick={() => setActiveTab("bouncers")}
              icon={<Radio className="w-5 h-5" />}
              tooltip="Bouncers"
            />
          </div>
        )}
        <div data-nav-id="ai">
          <NavIcon
            active={activeTab === "ai"}
            onClick={() => setActiveTab("ai")}
            icon={<Sparkles className="w-5 h-5" />}
            tooltip="AI Architect"
          />
        </div>
        {isAdmin(user) && (
          <div data-nav-id="admin">
            <NavIcon
              active={activeTab === "admin"}
              onClick={() => setActiveTab("admin")}
              icon={<Shield className="w-5 h-5" />}
              tooltip="Access Control"
            />
          </div>
        )}
      </div>

      {/* User + theme */}
      <div className="mt-auto flex flex-col items-center gap-4">
        <Tooltip>
          <TooltipTrigger
            className="p-1.5 text-text-muted hover:text-primary hover:bg-primary/10 rounded-lg transition-all duration-200 cursor-pointer"
            onClick={cycleTheme}
          >
            {themeIcon}
          </TooltipTrigger>
          <TooltipContent
            side="right"
            className="bg-card border-border-prominent text-foreground text-xs font-medium"
          >
            {themeLabel} (click to switch)
          </TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger
            className="p-1.5 text-text-muted hover:text-primary hover:bg-primary/10 rounded-lg transition-all duration-200 cursor-pointer"
            onClick={() => useOnboardingStore.getState().startOnboarding()}
          >
            <HelpCircle className="size-4" />
          </TooltipTrigger>
          <TooltipContent
            side="right"
            className="bg-card border-border-prominent text-foreground text-xs font-medium"
          >
            Restart tour
          </TooltipContent>
        </Tooltip>

        {/* Airflow status indicator removed — system works with manual data */}

        {/* User avatar + logout */}
        {user && (
          <div className="flex flex-col items-center gap-2">
            <Tooltip>
              <TooltipTrigger className="cursor-default">
                <UserInitials name={user.display_name} />
              </TooltipTrigger>
              <TooltipContent
                side="right"
                className="bg-card border-border-prominent text-foreground text-xs font-medium"
              >
                <div className="flex flex-col gap-0.5">
                  <span className="font-semibold">{user.display_name}</span>
                  <span className="text-text-secondary">{user.email}</span>
                  <span className="text-[10px] text-indigo-400 uppercase tracking-wider mt-0.5">
                    {user.role}
                  </span>
                </div>
              </TooltipContent>
            </Tooltip>

            {ssoEnabled && <SsoLogoutButton />}
          </div>
        )}
      </div>
    </nav>
  );
}
