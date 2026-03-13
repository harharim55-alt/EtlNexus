import { usePipelineStore } from "@/stores/pipeline-store";
import { X } from "lucide-react";
import { STATUS_CONFIG, STATUS_SEVERITY_ORDER } from "@/lib/status-config";
import { DateRangePicker } from "@/components/shared/DateRangePicker";

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
  availableStatuses: string[];
}

export function PipelineFilters({ availableTeams, availableDags, availableStatuses }: PipelineFiltersProps) {
  const { teamFilters, dagFilters, statusFilters, toggleFilter, clearAllFilters } =
    usePipelineStore();

  const hasActive = teamFilters.size > 0 || dagFilters.size > 0 || statusFilters.size > 0;

  // Sort statuses by severity order, with unknown statuses at the end
  const sortedStatuses = [...availableStatuses].sort((a, b) => {
    const ai = STATUS_SEVERITY_ORDER.indexOf(a);
    const bi = STATUS_SEVERITY_ORDER.indexOf(b);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

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

      {/* Status section — dynamically populated from actual pipeline data */}
      {sortedStatuses.length > 0 && (
        <FilterSection label="Status">
          {sortedStatuses.map((value) => {
            const cfg = STATUS_CONFIG[value] ?? STATUS_CONFIG.unknown;
            return (
              <button
                key={value}
                type="button"
                onClick={() => toggleFilter("status", value)}
                className={`text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer inline-flex items-center gap-1.5 ${
                  statusFilters.has(value) ? cfg.activePill : INACTIVE_PILL
                }`}
              >
                <span className={`size-1.5 rounded-full ${cfg.dot.replace(" animate-pulse", "")}`} />
                {cfg.label}
              </button>
            );
          })}
        </FilterSection>
      )}

      {/* Last Run date range */}
      <FilterSection label="Last Run">
        <DateRangePicker />
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
