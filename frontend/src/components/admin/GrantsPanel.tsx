import { useState } from "react";
import { ArrowRight, Plus, X } from "lucide-react";
import { useAdminGrants, useAdminTeams, useAdminUsers, useCreateGrant, useDeleteGrant } from "@/hooks/use-admin";
import { useQuery } from "@tanstack/react-query";
import { fetchPipelines } from "@/api/pipelines";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";

type GrantType = "pipeline" | "team";
type GranteeType = "team" | "user";

export function GrantsPanel() {
  const { data: grants, isLoading, error, refetch } = useAdminGrants();
  const { data: teams } = useAdminTeams();
  const { data: users } = useAdminUsers();
  const { data: pipelines } = useQuery({
    queryKey: ["pipelines"],
    queryFn: () => fetchPipelines(),
    staleTime: 2 * 60_000,
  });
  const createGrant = useCreateGrant();
  const removeGrant = useDeleteGrant();

  const [showForm, setShowForm] = useState(false);
  const [granteeType, setGranteeType] = useState<GranteeType>("team");
  const [granteeTeamId, setGranteeTeamId] = useState("");
  const [granteeUserId, setGranteeUserId] = useState("");
  const [grantType, setGrantType] = useState<GrantType>("pipeline");
  const [pipelineId, setPipelineId] = useState("");
  const [sourceTeamId, setSourceTeamId] = useState("");
  const [grantLevel, setGrantLevel] = useState<"viewer" | "editor">("viewer");

  const resetForm = () => {
    setGranteeType("team");
    setGranteeTeamId("");
    setGranteeUserId("");
    setGrantType("pipeline");
    setPipelineId("");
    setSourceTeamId("");
    setGrantLevel("viewer");
    setShowForm(false);
  };

  const handleCreate = () => {
    const hasGrantee = granteeType === "team" ? granteeTeamId : granteeUserId;
    const hasTarget = grantType === "pipeline" ? pipelineId : sourceTeamId;
    if (!hasGrantee || !hasTarget) return;

    const body = {
      ...(granteeType === "team"
        ? { grantee_team_id: granteeTeamId }
        : { grantee_user_id: granteeUserId }),
      ...(grantType === "pipeline"
        ? { pipeline_id: pipelineId }
        : { source_team_id: sourceTeamId }),
      grant_level: grantLevel,
    };

    createGrant.mutate(body, { onSuccess: resetForm });
  };

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message="Failed to load grants" onRetry={refetch} />;

  const teamMap = new Map((teams ?? []).map((t) => [t.id, t.name]));
  const pipelineMap = new Map((pipelines ?? []).map((p) => [p.id, p.name]));

  return (
    <div className="space-y-4">
      {/* Create grant form */}
      {showForm ? (
        <div className="bg-[#0f0f11] border border-indigo-500/20 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono text-indigo-400 uppercase tracking-wider">
              New Visibility Grant
            </h3>
            <button
              type="button"
              onClick={resetForm}
              className="text-slate-600 hover:text-slate-400 transition-colors cursor-pointer"
            >
              <X className="size-4" />
            </button>
          </div>

          {/* Grantee type toggle */}
          <div>
            <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1.5">
              Grant To
            </label>
            <div className="flex gap-1">
              {(["team", "user"] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => {
                    setGranteeType(type);
                    setGranteeTeamId("");
                    setGranteeUserId("");
                  }}
                  className={`text-xs font-mono px-3 py-1.5 rounded-lg border transition-all cursor-pointer ${
                    granteeType === type
                      ? "text-indigo-400 bg-indigo-500/10 border-indigo-500/20"
                      : "text-slate-600 border-white/[0.06] hover:text-slate-400 hover:border-white/10"
                  }`}
                >
                  {type === "team" ? "Team" : "User"}
                </button>
              ))}
            </div>
          </div>

          {/* Grantee selector */}
          <div>
            <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1.5">
              {granteeType === "team" ? "Grantee Team" : "Grantee User"}
            </label>
            {granteeType === "team" ? (
              <select
                value={granteeTeamId}
                onChange={(e) => setGranteeTeamId(e.target.value)}
                className="w-full bg-[#09090b] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500/40 transition-colors"
              >
                <option value="">Select team...</option>
                {(teams ?? []).map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            ) : (
              <select
                value={granteeUserId}
                onChange={(e) => setGranteeUserId(e.target.value)}
                className="w-full bg-[#09090b] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500/40 transition-colors"
              >
                <option value="">Select user...</option>
                {(users ?? []).map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.display_name} ({u.email})
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Grant type toggle */}
          <div>
            <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1.5">
              Access To
            </label>
            <div className="flex gap-1">
              {(["pipeline", "team"] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setGrantType(type)}
                  className={`text-xs font-mono px-3 py-1.5 rounded-lg border transition-all cursor-pointer ${
                    grantType === type
                      ? "text-indigo-400 bg-indigo-500/10 border-indigo-500/20"
                      : "text-slate-600 border-white/[0.06] hover:text-slate-400 hover:border-white/10"
                  }`}
                >
                  {type === "pipeline" ? "Single Pipeline" : "All Team Pipelines"}
                </button>
              ))}
            </div>
          </div>

          {/* Target selector */}
          <div>
            <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1.5">
              {grantType === "pipeline" ? "Pipeline" : "Source Team"}
            </label>
            {grantType === "pipeline" ? (
              <select
                value={pipelineId}
                onChange={(e) => setPipelineId(e.target.value)}
                className="w-full bg-[#09090b] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500/40 transition-colors"
              >
                <option value="">Select pipeline...</option>
                {(pipelines ?? []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            ) : (
              <select
                value={sourceTeamId}
                onChange={(e) => setSourceTeamId(e.target.value)}
                className="w-full bg-[#09090b] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500/40 transition-colors"
              >
                <option value="">Select team...</option>
                {(teams ?? [])
                  .filter((t) => t.id !== granteeTeamId)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
              </select>
            )}
          </div>

          {/* Permission level */}
          <div>
            <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1.5">
              Permission Level
            </label>
            <div className="flex gap-1">
              {(["viewer", "editor"] as const).map((level) => (
                <button
                  key={level}
                  type="button"
                  onClick={() => setGrantLevel(level)}
                  className={`text-xs font-mono px-3 py-1.5 rounded-lg border transition-all cursor-pointer ${
                    grantLevel === level
                      ? level === "editor"
                        ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                        : "text-indigo-400 bg-indigo-500/10 border-indigo-500/20"
                      : "text-slate-600 border-white/[0.06] hover:text-slate-400 hover:border-white/10"
                  }`}
                >
                  {level === "viewer" ? "Viewer" : "Editor"}
                </button>
              ))}
            </div>
            <p className="text-[10px] text-slate-600 mt-1">
              {grantLevel === "viewer"
                ? "Can view the pipeline but cannot edit description or documentation"
                : "Can view and edit description and documentation"}
            </p>
          </div>

          <button
            type="button"
            onClick={handleCreate}
            disabled={createGrant.isPending}
            className="w-full text-xs font-mono uppercase tracking-wider py-2.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 hover:bg-indigo-500/20 transition-all cursor-pointer disabled:opacity-40"
          >
            {createGrant.isPending ? "Creating..." : "Grant Access"}
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setShowForm(true)}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-dashed border-white/[0.06] text-slate-600 hover:text-indigo-400 hover:border-indigo-500/20 transition-all cursor-pointer"
        >
          <Plus className="size-3.5" />
          <span className="text-xs font-mono">New Grant</span>
        </button>
      )}

      {/* Grants list */}
      {!grants || grants.length === 0 ? (
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
                    grant.grant_level === "editor"
                      ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                      : "text-slate-400 bg-white/[0.03] border-white/[0.06]"
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
                    {new Date(grant.created_at).toLocaleDateString()}
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
        </div>
      )}
    </div>
  );
}
