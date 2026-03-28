import { useState } from "react";
import { Shield, Users, UsersRound, Eye } from "lucide-react";
import { useAdminUsers, useAdminTeams, useAdminGrants } from "@/hooks/use-admin";
import { UsersPanel } from "./UsersPanel";
import { TeamsPanel } from "./TeamsPanel";
import { GrantsPanel } from "./GrantsPanel";

type SubTab = "users" | "teams" | "grants";

const SUB_TABS: { key: SubTab; label: string; icon: typeof Users }[] = [
  { key: "users", label: "Users", icon: Users },
  { key: "teams", label: "Teams", icon: UsersRound },
  { key: "grants", label: "Grants", icon: Eye },
];

export function AdminView() {
  const [activeSubTab, setActiveSubTab] = useState<SubTab>("users");
  const { data: users } = useAdminUsers(activeSubTab === "users");
  const { data: teams } = useAdminTeams(activeSubTab === "teams");
  const { data: grants } = useAdminGrants(activeSubTab === "grants");

  return (
    <div data-section="admin-panel" className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="shrink-0 px-8 pt-8 pb-4">
        <div className="flex items-center gap-3 mb-5">
          <div className="bg-rose-500/10 p-2 rounded-lg border border-rose-500/20">
            <Shield className="w-5 h-5 text-rose-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-foreground">Access Control</h1>
            <p className="text-xs text-text-muted font-mono mt-0.5">
              {users?.pages[0]?.total ?? 0} users &middot; {teams?.length ?? 0} teams &middot;{" "}
              {grants?.pages[0]?.total ?? 0} grants
            </p>
          </div>
        </div>

        {/* Sub-tab buttons */}
        <div className="flex gap-1">
          {SUB_TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              type="button"
              onClick={() => setActiveSubTab(key)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-mono transition-all cursor-pointer ${
                activeSubTab === key
                  ? "bg-hover-bg-strong text-foreground border border-border"
                  : "text-text-muted border border-transparent hover:text-text-primary hover:bg-hover-bg"
              }`}
            >
              <Icon className="size-3.5" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-8 pb-8">
        {activeSubTab === "users" && <UsersPanel />}
        {activeSubTab === "teams" && <TeamsPanel />}
        {activeSubTab === "grants" && <GrantsPanel />}
      </div>
    </div>
  );
}
