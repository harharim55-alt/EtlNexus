import { useMemo } from "react";
import { ArrowRight, Plus, X } from "lucide-react";
import { formatDateAdmin } from "@/lib/format";
import { useAdminGrants, useAdminTeams, useAdminUsers, useDeleteGrant } from "@/hooks/use-admin";
import { useQuery } from "@tanstack/react-query";
import { fetchPipelines } from "@/api/pipelines";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { GRANT_LEVEL_STYLES } from "@/lib/admin-styles";
import { useGrantForm } from "./useGrantForm";
import { GrantForm } from "./GrantForm";

export function GrantsPanel() {
  const {
    data: grantsData,
    fetchNextPage: fetchNextGrants,
    hasNextPage: hasMoreGrants,
    isFetchingNextPage: isFetchingMoreGrants,
    isLoading,
    error,
    refetch,
  } = useAdminGrants();
  const grants = useMemo(
    () => grantsData?.pages.flatMap((p) => p.items) ?? [],
    [grantsData],
  );
  const { data: teams } = useAdminTeams();
  const { data: usersData } = useAdminUsers();
  const users = useMemo(
    () => usersData?.pages.flatMap((p) => p.items) ?? [],
    [usersData],
  );
  const { data: pipelinesData } = useQuery({
    queryKey: ["pipelines-lookup"],
    queryFn: () => fetchPipelines(undefined, 0, 500),
    staleTime: 2 * 60_000,
  });
  const removeGrant = useDeleteGrant();

  const form = useGrantForm();

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message="Failed to load grants" onRetry={refetch} />;

  const teamMap = new Map((teams ?? []).map((t) => [t.id, t.name]));
  const pipelineMap = new Map((pipelinesData?.items ?? []).map((p) => [p.id, p.name]));

  return (
    <div className="space-y-4">
      {/* Create grant form */}
      {form.showForm ? (
        <GrantForm
          granteeType={form.granteeType}
          granteeTeamId={form.granteeTeamId}
          granteeUserId={form.granteeUserId}
          grantType={form.grantType}
          pipelineId={form.pipelineId}
          sourceTeamId={form.sourceTeamId}
          grantLevel={form.grantLevel}
          teams={teams ?? []}
          users={users}
          pipelines={pipelinesData?.items ?? []}
          isPending={form.createGrant.isPending}
          onGranteeTypeChange={form.handleGranteeTypeChange}
          onGranteeTeamIdChange={form.setGranteeTeamId}
          onGranteeUserIdChange={form.setGranteeUserId}
          onGrantTypeChange={form.setGrantType}
          onPipelineIdChange={form.setPipelineId}
          onSourceTeamIdChange={form.setSourceTeamId}
          onGrantLevelChange={form.setGrantLevel}
          onSubmit={form.handleCreate}
          onCancel={form.resetForm}
        />
      ) : (
        <button
          type="button"
          onClick={() => form.setShowForm(true)}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-dashed border-white/[0.06] text-slate-600 hover:text-indigo-400 hover:border-indigo-500/20 transition-all cursor-pointer"
        >
          <Plus className="size-3.5" />
          <span className="text-xs font-mono">New Grant</span>
        </button>
      )}

      {/* Grants list */}
      {grants.length === 0 ? (
        <EmptyState message="No visibility grants configured" />
      ) : (
        <div className="space-y-2">
          {grants.map((grant) => {
            const granteeName = grant.grantee_team_name
              ?? grant.grantee_user_name
              ?? (grant.grantee_team_id ? teamMap.get(grant.grantee_team_id) : null)
              ?? "Unknown";
            const granteeDetail = grant.grantee_user_email
              ? grant.grantee_user_email
              : null;
            const isUserGrant = !!grant.grantee_user_id;
            const targetLabel = grant.pipeline_id
              ? pipelineMap.get(grant.pipeline_id) ?? grant.pipeline_id
              : grant.source_team_id
                ? `All of ${grant.source_team_name ?? teamMap.get(grant.source_team_id) ?? "Unknown"}`
                : "Unknown";

            return (
              <div
                key={grant.id}
                className="bg-[#0f0f11] border border-white/[0.04] rounded-xl p-4 flex items-center gap-3 hover:border-white/[0.08] transition-colors group"
              >
                {/* Grantee */}
                <div className="shrink-0 flex items-center gap-2">
                  <span
                    className={`text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded border ${
                      isUserGrant
                        ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                        : "text-indigo-400 bg-indigo-500/10 border-indigo-500/20"
                    }`}
                  >
                    {isUserGrant ? "user" : "team"}
                  </span>
                  <div>
                    <span className="text-sm font-medium text-white">
                      {granteeName}
                    </span>
                    {granteeDetail && (
                      <span className="text-[10px] text-slate-600 ml-1.5 font-mono">
                        {granteeDetail}
                      </span>
                    )}
                  </div>
                </div>

                <ArrowRight className="size-3.5 text-slate-600 shrink-0" />

                {/* Target */}
                <span
                  className={`text-sm shrink-0 ${
                    grant.pipeline_id
                      ? "text-indigo-400 font-mono"
                      : "text-teal-400"
                  }`}
                >
                  {targetLabel}
                </span>

                {/* Grant level badge */}
                <span
                  className={`text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded border shrink-0 ${
                    GRANT_LEVEL_STYLES[grant.grant_level] ?? GRANT_LEVEL_STYLES.viewer
                  }`}
                >
                  {grant.grant_level}
                </span>

                {/* Meta */}
                <div className="flex-1 flex items-center justify-end gap-3">
                  <span className="text-[10px] font-mono text-slate-600">
                    by {grant.granted_by}
                  </span>
                  <span className="text-[10px] font-mono text-slate-600">
                    {formatDateAdmin(grant.created_at)}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeGrant.mutate(grant.id)}
                    disabled={removeGrant.isPending}
                    className="opacity-0 group-hover:opacity-100 p-1 text-slate-600 hover:text-rose-400 hover:bg-rose-500/10 rounded-md transition-all cursor-pointer"
                  >
                    <X className="size-3.5" />
                  </button>
                </div>
              </div>
            );
          })}

          {hasMoreGrants && (
            <button
              type="button"
              onClick={() => fetchNextGrants()}
              disabled={isFetchingMoreGrants}
              className="w-full py-3 rounded-xl border border-dashed border-white/[0.06] text-slate-600 hover:text-indigo-400 hover:border-indigo-500/20 transition-all cursor-pointer text-xs font-mono disabled:opacity-40"
            >
              {isFetchingMoreGrants
                ? "Loading..."
                : `Load more (${grants.length} of ${grantsData?.pages[0]?.total ?? 0})`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
