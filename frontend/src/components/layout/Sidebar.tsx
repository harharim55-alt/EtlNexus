import { Activity, Database, Network, Sparkles } from "lucide-react";
import { useNavigationStore } from "@/stores/navigation-store";
import { useAirflowStatuses } from "@/hooks/use-airflow-status";
import { NavIcon } from "./NavIcon";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function Sidebar() {
  const { activeTab, setActiveTab } = useNavigationStore();
  const { data: airflowData } = useAirflowStatuses();

  return (
    <nav className="w-20 border-r border-white/5 bg-[#09090b] flex flex-col items-center py-6 z-20 shrink-0">
      {/* Logo */}
      <div className="mb-8">
        <img src="/logo.svg" alt="ETL Nexus" className="w-11 h-11" />
      </div>

      {/* Nav Icons */}
      <div className="flex-1 flex flex-col gap-4 w-full px-3">
        <NavIcon
          active={activeTab === "catalog"}
          onClick={() => setActiveTab("catalog")}
          icon={<Database className="w-5 h-5" />}
          tooltip="ETL Catalog"
        />
        <NavIcon
          active={activeTab === "matrix"}
          onClick={() => setActiveTab("matrix")}
          icon={<Network className="w-5 h-5" />}
          tooltip="Field Matrix"
        />
        <NavIcon
          active={activeTab === "ai"}
          onClick={() => setActiveTab("ai")}
          icon={<Sparkles className="w-5 h-5" />}
          tooltip="AI Architect"
        />
      </div>

      {/* Airflow Status */}
      <div className="mt-auto">
        <Tooltip>
          <TooltipTrigger className="cursor-pointer">
            <Activity
              className={`w-5 h-5 ${
                airflowData?.airflow_connected
                  ? "text-emerald-400"
                  : "text-slate-600"
              }`}
            />
          </TooltipTrigger>
          <TooltipContent
            side="right"
            className="bg-[#18181b] border-white/10 text-white text-xs font-medium"
          >
            Airflow: {airflowData?.airflow_connected ? "Online" : "Offline"}
          </TooltipContent>
        </Tooltip>
      </div>
    </nav>
  );
}
