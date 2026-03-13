import { useMemo, useState } from "react";
import { ArrowRight, ChevronDown, Users } from "lucide-react";
import { useAdminTeams, useAdminGrants, useTeamDetail } from "@/hooks/use-admin";
import { useQuery } from "@tanstack/react-query";
import { fetchPipelines } from "@/api/pipelines";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { UserInitials } from "@/components/shared/UserInitials";
import { ROLE_STYLES, GRANT_LEVEL_STYLES } from "@/lib/admin-styles";

const SOURCE_STYLES: Record<string, string> = {
  sso: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
  airflow: "text-teal-400 bg-teal-500/10 border-teal-500/20",
  manual: "text-amber-400 bg-amber-500/10 border-amber-500/20",
};

function TeamDetailSection({ teamId }: { teamId: string }) {
  const { data: detail, isLoading } = useTeamDetail(teamId);
  const { data: grantsData } = useAdminGrants();
  const { data: teams } = useAdminTeams();
  const { data: pipelinesData } = useQuery({
    queryKey: ["pipelines-lookup"],
    queryFn: () => fetchPipelines(undefined, 0, 500),
    staleTime: 2 * 60_000,
  });

  const teamMap = useMemo(
    () => new Map((teams ?? []).map((t) => [t.id, t.name])),
    [teams],
  );
  const pipelineMap = useMemo(
    () => new Map((pipelinesData?.items ?? []).map((p) => [p.id, p.name])),
    [pipelinesData],
  );

  const allGrants = useMemo(
    () => grantsData?.pages.flatMap((p) => p.items) ?? [],
    [grantsData],
  );
  const teamGrants = useMemo(
    () => allGrants.filter((g) => g.grantee_team_id === teamId),
    [allGrants, teamId],
  );

  if (isLoading) {
    return (
      <div className="flex items-center gap-1 py-3">
        <div className="w-1.5 h-4 bg-indigo-500/30 rounded animate-pulse" />
        <div className="w-1.5 h-6 bg-indigo-500/50 rounded animate-pulse delay-75" />
        <div className="w-1.5 h-3 bg-indigo-500/20 rounded animate-pulse delay-150" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Members */}
      <div>
        <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
          Members ({detail?.members.length ?? 0})
        </span>
        {!detail?.members.length ? (
          <p className="text-xs text-slate-600 mt-2">No members</p>
        ) : (
          <div className="mt-2 space-y-1.5">
            {detail.members.map((m) => (
              <div
                key={m.id}
                className="flex items-center gap-3 py-1.5 px-3 rounded-lg bg-white/[0.02]"
              >
                <UserInitials name={m.display_name} size="sm" />
                <div className="flex-1 min-w-0">
                  <span className="text-xs text-white font-medium truncate block">
                    {m.display_name}
                  </span>
                  <span className="text-[10px] text-slate-600 font-mono truncate block">
                    {m.email}
                  </span>
                </div>
                <span
                  className={`text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded border ${ROLE_STYLES[m.role] ?? ROLE_STYLES.member}`}
                >
                  {m.role}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Grants */}
      <div>
        <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
          Team Grants ({teamGrants.length})
        </span>
        {teamGrants.length === 0 ? (
          <p className="text-xs text-slate-600 mt-2">No grants for this team</p>
        ) : (
          <div className="mt-2 space-y-1.5">
            {teamGrants.map((g) => {
              const target = g.pipeline_id
                ? pipelineMap.get(g.pipeline_id) ?? g.pipeline_id
                : g.source_team_id
                  ? `All of ${g.source_team_name ?? teamMap.get(g.source_team_id) ?? "Unknown"}`
                  : "Unknown";
              return (
                <div
                  key={g.id}
                  className="flex items-center gap-2 py-1.5 px-3 rounded-lg bg-white/[0.02]"
                >
                  <ArrowRight className="size-3 text-slate-600 shrink-0" />
                  <span
                    className={`text-xs ${
                      g.pipeline_id
                        ? "text-indigo-400 font-mono"
                        : "text-teal-400"
                    }`}
                  >
                    {target}
                  </span>
                  <span
                    className={`text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded border shrink-0 ${
                      GRANT_LEVEL_STYLES[g.grant_level] ?? GRANT_LEVEL_STYLES.viewer
                    }`}
                  >
                    {g.grant_level}
                  </span>
                  <span className="text-[10px] font-mono text-slate-600 ml-auto">
                    {new Date(g.created_at).toLocaleDateString()}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export function TeamsPanel() {
  const { data: teams, isLoading, error, refetch } = useAdminTeams();
  const [expandedTeamId, setExpandedTeamId] = useState<string | null>(null);

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message="Failed to load teams" onRetry={refetch} />;
  if (!teams || teams.length === 0) return <EmptyState message="No teams found" />;

  const toggleExpand = (teamId: string) => {
    setExpandedTeamId((prev) => (prev === teamId ? null : teamId));
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
      {teams.map((team) => {
        const isExpanded = expandedTeamId === team.id;
        return (
          <div
            key={team.id}
            className={`bg-[#0f0f11] border rounded-xl transition-colors ${
              isExpanded
                ? "border-indigo-500/20 lg:col-span-2"
                : "border-white/[0.04] hover:border-white/[0.08]"
            }`}
          >
            <div
              className="p-5 cursor-pointer"
              onClick={() => toggleExpand(team.id)}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-sm font-medium text-white">{team.name}</h3>
                  {team.description && (
                    <p className="text-xs text-slate-500 mt-0.5">
                      {team.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded border ${SOURCE_STYLES[team.source] ?? SOURCE_STYLES.manual}`}
                  >
                    {team.source}
                  </span>
                  <ChevronDown
                    className={`size-4 text-slate-600 transition-transform ${
                      isExpanded ? "rotate-180" : ""
                    }`}
                  />
                </div>
              </div>

              <div className="flex items-center gap-1.5 text-slate-500">
                <Users className="size-3.5" />
                <span className="text-xs font-mono">
                  {team.member_count} member{team.member_count !== 1 ? "s" : ""}
                </span>
              </div>
            </div>

            {/* Expanded detail */}
            {isExpanded && (
              <div className="px-5 pb-5 pt-0 border-t border-white/[0.04]">
                <div className="pt-3">
                  <TeamDetailSection teamId={team.id} />
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
