import { X } from "lucide-react";
import { stripDummy } from "@/lib/format";
import type { GrantType, GranteeType } from "./useGrantForm";

/* ── Types ────────────────────────────────────────────────────────── */

interface TeamOption {
  id: string;
  name: string;
}

interface UserOption {
  id: string;
  display_name: string;
  email: string;
}

interface PipelineOption {
  id: string;
  name: string;
}

interface GrantFormProps {
  granteeType: GranteeType;
  granteeTeamId: string;
  granteeUserId: string;
  grantType: GrantType;
  pipelineId: string;
  sourceTeamId: string;
  grantLevel: "viewer" | "editor";
  teams: TeamOption[];
  users: UserOption[];
  pipelines: PipelineOption[];
  isPending: boolean;
  onGranteeTypeChange: (type: GranteeType) => void;
  onGranteeTeamIdChange: (id: string) => void;
  onGranteeUserIdChange: (id: string) => void;
  onGrantTypeChange: (type: GrantType) => void;
  onPipelineIdChange: (id: string) => void;
  onSourceTeamIdChange: (id: string) => void;
  onGrantLevelChange: (level: "viewer" | "editor") => void;
  onSubmit: () => void;
  onCancel: () => void;
}

/* ── Component ─────────────────────────────────────────────────────── */

export function GrantForm({
  granteeType,
  granteeTeamId,
  granteeUserId,
  grantType,
  pipelineId,
  sourceTeamId,
  grantLevel,
  teams,
  users,
  pipelines,
  isPending,
  onGranteeTypeChange,
  onGranteeTeamIdChange,
  onGranteeUserIdChange,
  onGrantTypeChange,
  onPipelineIdChange,
  onSourceTeamIdChange,
  onGrantLevelChange,
  onSubmit,
  onCancel,
}: GrantFormProps) {
  return (
    <div className="bg-[#0f0f11] border border-indigo-500/20 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-mono text-indigo-400 uppercase tracking-wider">
          New Visibility Grant
        </h3>
        <button
          type="button"
          onClick={onCancel}
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
              onClick={() => onGranteeTypeChange(type)}
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
            onChange={(e) => onGranteeTeamIdChange(e.target.value)}
            className="w-full bg-[#09090b] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500/40 transition-colors"
          >
            <option value="">Select team...</option>
            {teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        ) : (
          <select
            value={granteeUserId}
            onChange={(e) => onGranteeUserIdChange(e.target.value)}
            className="w-full bg-[#09090b] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500/40 transition-colors"
          >
            <option value="">Select user...</option>
            {users.map((u) => (
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
              onClick={() => onGrantTypeChange(type)}
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
            onChange={(e) => onPipelineIdChange(e.target.value)}
            className="w-full bg-[#09090b] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500/40 transition-colors"
          >
            <option value="">Select pipeline...</option>
            {pipelines.map((p) => (
              <option key={p.id} value={p.id}>
                {stripDummy(p.name)}
              </option>
            ))}
          </select>
        ) : (
          <select
            value={sourceTeamId}
            onChange={(e) => onSourceTeamIdChange(e.target.value)}
            className="w-full bg-[#09090b] border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500/40 transition-colors"
          >
            <option value="">Select team...</option>
            {teams
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
              onClick={() => onGrantLevelChange(level)}
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
        onClick={onSubmit}
        disabled={isPending}
        className="w-full text-xs font-mono uppercase tracking-wider py-2.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 hover:bg-indigo-500/20 transition-all cursor-pointer disabled:opacity-40"
      >
        {isPending ? "Creating..." : "Grant Access"}
      </button>
    </div>
  );
}
