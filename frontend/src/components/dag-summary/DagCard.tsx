import { useState, memo } from "react";
import { AlertTriangle, ChevronDown, Pause } from "lucide-react";
import { getStatusStyle, STATUS_SEVERITY_ORDER } from "@/lib/status-config";
import { DagMetrics } from "./DagMetrics";
import { DagTaskList } from "./DagTaskList";
import type { DagSummary } from "@/types/dag-summary";

function formatDagName(dagId: string): string {
  return dagId
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function statusGlow(dag: DagSummary): string {
  if (dag.is_paused) return "bg-slate-600";
  for (const s of STATUS_SEVERITY_ORDER) {
    if ((dag.status_counts[s] ?? 0) > 0) {
      const cfg = getStatusStyle(s);
      return `${cfg.dot.replace(" animate-pulse", "")} ${cfg.glow}`;
    }
  }
  return "bg-slate-600";
}

interface DagCardProps {
  dag: DagSummary;
}

export const DagCard = memo(function DagCard({ dag }: DagCardProps) {
  const [showFailed, setShowFailed] = useState(false);
  const failedTotal = (dag.status_counts.failed ?? 0) + (dag.status_counts.upstream_failed ?? 0);

  return (
    <div className="bg-[#18181b] border border-white/5 rounded-2xl p-5 flex flex-col gap-4 hover:border-white/10 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${statusGlow(dag)}`} />
          <h3 className="text-base font-semibold text-white font-mono truncate">
            {formatDagName(dag.dag_id)}
          </h3>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {failedTotal > 0 && (
            <button
              onClick={() => setShowFailed(!showFailed)}
              className="flex items-center gap-1 text-[9px] font-mono uppercase tracking-widest text-rose-400/90 bg-rose-500/10 px-2 py-0.5 rounded-full border border-rose-500/20 hover:bg-rose-500/20 transition-colors cursor-pointer"
            >
              <AlertTriangle className="w-2.5 h-2.5" />
              {failedTotal} failed
              <ChevronDown
                className={`w-2.5 h-2.5 transition-transform ${showFailed ? "rotate-180" : ""}`}
              />
            </button>
          )}
          {dag.is_paused && (
            <span className="flex items-center gap-1 text-[9px] font-mono uppercase tracking-widest text-amber-500/80 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
              <Pause className="w-2.5 h-2.5" />
              Paused
            </span>
          )}
        </div>
      </div>

      {/* Metrics sections */}
      <DagMetrics dag={dag} showFailed={showFailed} />

      {/* Task Status Dots */}
      <DagTaskList tasks={dag.tasks} />
    </div>
  );
});
