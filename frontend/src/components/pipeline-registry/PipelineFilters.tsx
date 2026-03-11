import { usePipelineStore } from "@/stores/pipeline-store";
import { X } from "lucide-react";

const STATUS_CONFIG = [
  { value: "success", label: "Success", dot: "bg-emerald-500", active: "text-emerald-300 bg-emerald-500/15 border-emerald-500/30" },
  { value: "failed", label: "Failed", dot: "bg-rose-500", active: "text-rose-300 bg-rose-500/15 border-rose-500/30" },
  { value: "running", label: "Running", dot: "bg-amber-500", active: "text-amber-300 bg-amber-500/15 border-amber-500/30" },
  { value: "unknown", label: "Unknown", dot: "bg-slate-500", active: "text-slate-300 bg-slate-500/15 border-slate-500/30" },
] as const;

const INACTIVE_PILL =
  "text-slate-500 bg-white/[0.02] border-white/5 hover:border-white/15 hover:text-slate-400";

function formatDagLabel(dagId: string) {
  return dagId
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

interface PipelineFiltersProps {
  availableTeams: string[];
  availableDags: string[];
}

export function PipelineFilters({ availableTeams, availableDags }: PipelineFiltersProps) {
  const { teamFilters, dagFilters, statusFilters, toggleFilter, clearAllFilters } =
    usePipelineStore();

  const hasActive = teamFilters.size > 0 || dagFilters.size > 0 || statusFilters.size > 0;

  return (
    <div className="px-5 pb-4 pt-1 border-b border-white/5 animate-in fade-in slide-in-from-top-2 duration-200 space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono uppercase tracking-widest text-slate-600">
          Filters
        </span>
        {hasActive && (
          <button
            type="button"
            onClick={clearAllFilters}
            className="text-[10px] font-mono text-slate-500 hover:text-indigo-400 transition-colors cursor-pointer flex items-center gap-1"
          >
            <X className="size-3" />
            Clear all
          </button>
        )}
      </div>

      {/* Team section */}
      {availableTeams.length > 0 && (
        <FilterSection label="Team">
          {availableTeams.map((team) => (
            <button
              key={team}
              type="button"
              onClick={() => toggleFilter("team", team)}
              className={`text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer ${
                teamFilters.has(team)
                  ? "text-indigo-300 bg-indigo-500/15 border-indigo-500/30 shadow-[0_0_8px_rgba(99,102,241,0.12)]"
                  : INACTIVE_PILL
              }`}
            >
              {team}
            </button>
          ))}
        </FilterSection>
      )}

      {/* DAG / Network section */}
      {availableDags.length > 0 && (
        <FilterSection label="Network">
          {availableDags.map((dagId) => (
            <button
              key={dagId}
              type="button"
              onClick={() => toggleFilter("dag", dagId)}
              className={`text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer ${
                dagFilters.has(dagId)
                  ? "text-teal-300 bg-teal-500/15 border-teal-500/30 shadow-[0_0_8px_rgba(45,212,191,0.12)]"
                  : INACTIVE_PILL
              }`}
            >
              {formatDagLabel(dagId)}
            </button>
          ))}
        </FilterSection>
      )}

      {/* Status section */}
      <FilterSection label="Status">
        {STATUS_CONFIG.map((s) => (
          <button
            key={s.value}
            type="button"
            onClick={() => toggleFilter("status", s.value)}
            className={`text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer inline-flex items-center gap-1.5 ${
              statusFilters.has(s.value) ? s.active : INACTIVE_PILL
            }`}
          >
            <span className={`size-1.5 rounded-full ${s.dot}`} />
            {s.label}
          </button>
        ))}
      </FilterSection>
    </div>
  );
}

function FilterSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <span className="text-[9px] font-mono uppercase tracking-widest text-slate-600">
          {label}
        </span>
        <div className="flex-1 h-px bg-white/5" />
      </div>
      <div className="flex items-center gap-1.5 flex-wrap">{children}</div>
    </div>
  );
}
