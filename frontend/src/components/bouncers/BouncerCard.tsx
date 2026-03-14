import { Check, Radio } from "lucide-react";
import { useBouncerStore } from "@/stores/bouncer-store";
import { getStatusStyle } from "@/lib/status-config";
import type { Bouncer } from "@/types/bouncer";

const TEAM_TAG_COLORS: Record<string, string> = {
  "Infrastructure Ops": "text-sky-400/70 bg-sky-500/8 border-sky-500/15",
  "Network Monitoring": "text-violet-400/70 bg-violet-500/8 border-violet-500/15",
  "Security Engineering": "text-rose-400/70 bg-rose-500/8 border-rose-500/15",
  "NOC Operations": "text-amber-400/70 bg-amber-500/8 border-amber-500/15",
};

function formatVolume(volume: number | null): string {
  if (volume === null) return "--";
  if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(1)}M`;
  if (volume >= 1_000) return `${(volume / 1_000).toFixed(0)}K`;
  return String(volume);
}

interface BouncerCardProps {
  bouncer: Bouncer;
}

export function BouncerCard({ bouncer }: BouncerCardProps) {
  const selectedBouncers = useBouncerStore((s) => s.selectedBouncers);
  const toggleBouncer = useBouncerStore((s) => s.toggleBouncer);
  const isSelected = selectedBouncers.includes(bouncer.bouncer_name);
  const status = bouncer.status || "unknown";
  const cfg = getStatusStyle(status);
  const teamColors =
    TEAM_TAG_COLORS[bouncer.team || ""] ||
    "text-slate-400/70 bg-white/[0.03] border-white/5";

  return (
    <button
      type="button"
      onClick={() => toggleBouncer(bouncer.bouncer_name)}
      className={`
        group relative w-full text-left rounded-xl border p-4 transition-all duration-200 cursor-pointer
        ${
          isSelected
            ? "bg-teal-500/[0.06] border-teal-500/25 shadow-[0_0_20px_rgba(45,212,191,0.12)]"
            : "bg-[#18181b] border-white/5 hover:border-white/10 hover:bg-white/[0.02]"
        }
      `}
    >
      {/* Selection indicator */}
      <div
        className={`absolute top-3 right-3 w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all ${
          isSelected
            ? "bg-teal-500 border-teal-500"
            : "border-white/15 group-hover:border-white/25"
        }`}
      >
        {isSelected && <Check className="w-3 h-3 text-white" strokeWidth={3} />}
      </div>

      {/* Header: icon + name + status */}
      <div className="flex items-start gap-3 mb-3 pr-6">
        <div
          className={`shrink-0 p-1.5 rounded-lg transition-colors ${
            isSelected
              ? "bg-teal-500/15"
              : "bg-white/[0.03] group-hover:bg-white/[0.05]"
          }`}
        >
          <Radio
            className={`w-3.5 h-3.5 ${
              isSelected ? "text-teal-400" : "text-slate-500"
            }`}
          />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-0.5">
            <span
              className={`inline-block w-2 h-2 rounded-full shrink-0 ${cfg.dot} ${cfg.glow}`}
            />
            <h4
              className={`text-xs font-medium truncate ${
                isSelected ? "text-teal-200" : "text-slate-200"
              }`}
            >
              {bouncer.display_name}
            </h4>
          </div>
          <p className="text-[9px] font-mono text-slate-600 truncate">
            {bouncer.bouncer_name}
          </p>
        </div>
      </div>

      {/* Volume hero metric */}
      <div className="mb-3">
        <div className="flex items-end gap-1.5">
          <span
            className={`text-2xl font-semibold font-mono tracking-tight leading-none ${
              isSelected ? "text-teal-300" : "text-white"
            }`}
          >
            {formatVolume(bouncer.volume_per_day)}
          </span>
          <span className="text-[9px] font-mono text-slate-600 mb-0.5">
            events/day
          </span>
        </div>
      </div>

      {/* Team badge */}
      {bouncer.team && (
        <div className="mb-3">
          <span
            className={`inline-flex text-[9px] font-mono px-2 py-0.5 rounded-full border ${teamColors}`}
          >
            {bouncer.team}
          </span>
        </div>
      )}

      {/* Description */}
      {bouncer.description && (
        <p className="text-[10px] text-slate-500 leading-relaxed line-clamp-2 mb-3">
          {bouncer.description}
        </p>
      )}

      {/* DAG pills */}
      {bouncer.dag_ids.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[8px] font-mono uppercase tracking-widest text-slate-600 mr-0.5">
            DAGs
          </span>
          {bouncer.dag_ids.map((dagId) => (
            <span
              key={dagId}
              className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-white/[0.03] text-slate-500 border border-white/5"
            >
              {dagId.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}

      {/* Hover gradient effect */}
      <div
        className={`absolute inset-0 rounded-xl pointer-events-none transition-opacity duration-300 ${
          isSelected
            ? "opacity-100 bg-[radial-gradient(ellipse_at_top_left,rgba(45,212,191,0.04),transparent_60%)]"
            : "opacity-0 group-hover:opacity-100 bg-[radial-gradient(ellipse_at_top_left,rgba(45,212,191,0.02),transparent_60%)]"
        }`}
      />
    </button>
  );
}
