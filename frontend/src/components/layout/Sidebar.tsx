import { useState } from "react";
import { Activity, BarChart3, Database, HelpCircle, LogOut, Network, Radio, RefreshCw, Shield, Sparkles } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useNavigationStore } from "@/stores/navigation-store";
import { useAirflowStatuses } from "@/hooks/use-airflow-status";
import { useAuthStore } from "@/stores/auth-store";
import { useOnboardingStore } from "@/stores/onboarding-store";
import { isAdmin } from "@/lib/permissions";
import { AIRFLOW_URL } from "@/lib/config";
import { syncAllPipelines } from "@/api/airflow";
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
        className="p-1.5 text-slate-600 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all duration-200 cursor-pointer"
        onClick={handleLogout}
      >
        <LogOut className="size-4" />
      </TooltipTrigger>
      <TooltipContent
        side="right"
        className="bg-[#18181b] border-white/10 text-white text-xs font-medium"
      >
        Sign out
      </TooltipContent>
    </Tooltip>
  );
}

export function Sidebar() {
  const { activeTab, setActiveTab } = useNavigationStore();
  const { data: airflowData } = useAirflowStatuses();
  const user = useAuthStore((s) => s.user);
  const ssoEnabled = useAuthStore((s) => s.ssoEnabled);
  const [isSyncingAll, setIsSyncingAll] = useState(false);
  const queryClient = useQueryClient();

  return (
    <nav className="w-20 border-r border-white/5 bg-[#09090b] flex flex-col items-center py-6 z-20 shrink-0">
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
        <div data-nav-id="matrix">
          <NavIcon
            active={activeTab === "matrix"}
            onClick={() => setActiveTab("matrix")}
            icon={<Network className="w-5 h-5" />}
            tooltip="Field Matrix"
          />
        </div>
        <div data-nav-id="dags">
          <NavIcon
            active={activeTab === "dags"}
            onClick={() => setActiveTab("dags")}
            icon={<BarChart3 className="w-5 h-5" />}
            tooltip="DAG Summary"
          />
        </div>
        <div data-nav-id="bouncers">
          <NavIcon
            active={activeTab === "bouncers"}
            onClick={() => setActiveTab("bouncers")}
            icon={<Radio className="w-5 h-5" />}
            tooltip="Bouncers"
          />
        </div>
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

      {/* Airflow Status + User */}
      <div className="mt-auto flex flex-col items-center gap-4">
        {isAdmin(user) && (
          <Tooltip>
            <TooltipTrigger
              className={`p-1.5 rounded-lg transition-all duration-200 cursor-pointer ${
                isSyncingAll
                  ? "text-amber-400 bg-amber-500/10"
                  : "text-slate-600 hover:text-amber-400 hover:bg-amber-500/10"
              }`}
              onClick={async () => {
                if (isSyncingAll) return;
                setIsSyncingAll(true);
                try {
                  const result = await syncAllPipelines();
                  toast.success(`Synced ${result.synced} pipelines from Airflow`);
                  queryClient.invalidateQueries({ queryKey: ["pipelines"] });
                  queryClient.invalidateQueries({ queryKey: ["airflow-statuses"] });
                  queryClient.invalidateQueries({ queryKey: ["dag-summary"] });
                  queryClient.invalidateQueries({ queryKey: ["topology"] });
                  queryClient.invalidateQueries({ queryKey: ["lineage"] });
                  queryClient.invalidateQueries({ queryKey: ["resource-metrics"] });
                  queryClient.invalidateQueries({ queryKey: ["pipeline-runs"] });
                  queryClient.invalidateQueries({ queryKey: ["execution-plan"] });
                  queryClient.invalidateQueries({ queryKey: ["execution-plan-runs"] });
                  queryClient.invalidateQueries({ queryKey: ["resource-history"] });
                } catch {
                  toast.error("Failed to sync pipelines from Airflow");
                } finally {
                  setIsSyncingAll(false);
                }
              }}
            >
              <RefreshCw className={`size-4 ${isSyncingAll ? "animate-spin" : ""}`} />
            </TooltipTrigger>
            <TooltipContent
              side="right"
              className="bg-[#18181b] border-white/10 text-white text-xs font-medium"
            >
              {isSyncingAll ? "Syncing all pipelines..." : "Sync all pipelines"}
            </TooltipContent>
          </Tooltip>
        )}

        <Tooltip>
          <TooltipTrigger
            className="p-1.5 text-slate-600 hover:text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-all duration-200 cursor-pointer"
            onClick={() => useOnboardingStore.getState().startOnboarding()}
          >
            <HelpCircle className="size-4" />
          </TooltipTrigger>
          <TooltipContent
            side="right"
            className="bg-[#18181b] border-white/10 text-white text-xs font-medium"
          >
            Restart tour
          </TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger>
            <a
              href={AIRFLOW_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="cursor-pointer"
            >
              <Activity
                className={`w-5 h-5 ${
                  airflowData?.airflow_connected
                    ? "text-emerald-400"
                    : "text-slate-600"
                }`}
              />
            </a>
          </TooltipTrigger>
          <TooltipContent
            side="right"
            className="bg-[#18181b] border-white/10 text-white text-xs font-medium"
          >
            Airflow: {airflowData?.airflow_connected ? "Online" : "Offline"}
          </TooltipContent>
        </Tooltip>

        {/* User avatar + logout */}
        {user && (
          <div className="flex flex-col items-center gap-2">
            <Tooltip>
              <TooltipTrigger className="cursor-default">
                <UserInitials name={user.display_name} />
              </TooltipTrigger>
              <TooltipContent
                side="right"
                className="bg-[#18181b] border-white/10 text-white text-xs font-medium"
              >
                <div className="flex flex-col gap-0.5">
                  <span className="font-semibold">{user.display_name}</span>
                  <span className="text-slate-400">{user.email}</span>
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
