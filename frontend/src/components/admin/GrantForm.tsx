import { X } from "lucide-react";
import { stripDummy } from "@/lib/format";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
    <div className="bg-surface-alt border border-indigo-500/20 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-mono text-indigo-400 uppercase tracking-wider">
          New Visibility Grant
        </h3>
        <button
          type="button"
          onClick={onCancel}
          className="text-text-faint hover:text-text-secondary transition-colors cursor-pointer"
        >
          <X className="size-4" />
        </button>
      </div>

      {/* Grantee type toggle */}
      <div>
        <label className="text-[10px] font-mono text-text-muted uppercase tracking-wider block mb-1.5">
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
                  : "text-text-faint border-border hover:text-text-secondary hover:border-border-prominent"
              }`}
            >
              {type === "team" ? "Team" : "User"}
            </button>
          ))}
        </div>
      </div>

      {/* Grantee selector */}
      <div>
        <label className="text-[10px] font-mono text-text-muted uppercase tracking-wider block mb-1.5">
          {granteeType === "team" ? "Grantee Team" : "Grantee User"}
        </label>
        {granteeType === "team" ? (
          <Select value={granteeTeamId} onValueChange={(v) => onGranteeTeamIdChange(v ?? "")}>
            <SelectTrigger className="w-full bg-background border-border text-foreground focus-visible:border-indigo-500/40 focus-visible:ring-indigo-500/20">
              <SelectValue placeholder="Select team..." />
            </SelectTrigger>
            <SelectContent className="bg-card border-border-prominent">
              {teams.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <Select value={granteeUserId} onValueChange={(v) => onGranteeUserIdChange(v ?? "")}>
            <SelectTrigger className="w-full bg-background border-border text-foreground focus-visible:border-indigo-500/40 focus-visible:ring-indigo-500/20">
              <SelectValue placeholder="Select user..." />
            </SelectTrigger>
            <SelectContent className="bg-card border-border-prominent">
              {users.map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.display_name} ({u.email})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Grant type toggle */}
      <div>
        <label className="text-[10px] font-mono text-text-muted uppercase tracking-wider block mb-1.5">
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
                  : "text-text-faint border-border hover:text-text-secondary hover:border-border-prominent"
              }`}
            >
              {type === "pipeline" ? "Single Pipeline" : "All Team Pipelines"}
            </button>
          ))}
        </div>
      </div>

      {/* Target selector */}
      <div>
        <label className="text-[10px] font-mono text-text-muted uppercase tracking-wider block mb-1.5">
          {grantType === "pipeline" ? "Pipeline" : "Source Team"}
        </label>
        {grantType === "pipeline" ? (
          <Select value={pipelineId} onValueChange={(v) => onPipelineIdChange(v ?? "")}>
            <SelectTrigger className="w-full bg-background border-border text-foreground focus-visible:border-indigo-500/40 focus-visible:ring-indigo-500/20">
              <SelectValue placeholder="Select pipeline..." />
            </SelectTrigger>
            <SelectContent className="bg-card border-border-prominent">
              {pipelines.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {stripDummy(p.name)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <Select value={sourceTeamId} onValueChange={(v) => onSourceTeamIdChange(v ?? "")}>
            <SelectTrigger className="w-full bg-background border-border text-foreground focus-visible:border-indigo-500/40 focus-visible:ring-indigo-500/20">
              <SelectValue placeholder="Select team..." />
            </SelectTrigger>
            <SelectContent className="bg-card border-border-prominent">
              {teams
                .filter((t) => t.id !== granteeTeamId)
                .map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Permission level */}
      <div>
        <label className="text-[10px] font-mono text-text-muted uppercase tracking-wider block mb-1.5">
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
                  : "text-text-faint border-border hover:text-text-secondary hover:border-border-prominent"
              }`}
            >
              {level === "viewer" ? "Viewer" : "Editor"}
            </button>
          ))}
        </div>
        <p className="text-[10px] text-text-faint mt-1">
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
