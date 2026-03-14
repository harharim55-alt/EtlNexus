import { useState, memo } from "react";
import { Clock, Layers, Timer, Workflow, CheckCircle, Pause, CalendarClock, AlertTriangle, ChevronDown } from "lucide-react";
import { TaskStatusDots } from "./TaskStatusDots";
import { getStatusStyle, STATUS_SEVERITY_ORDER } from "@/lib/status-config";
import { formatDuration } from "@/lib/format";
import type { DagSummary, DagTaskSummary } from "@/types/dag-summary";

function formatDagName(dagId: string): string {
  return dagId
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function formatGroupName(groupId: string): string {
  return groupId.replace(/_/g, " ");
}

function successRateColor(rate: number | null): string {
  if (rate === null) return "text-slate-500";
  if (rate >= 90) return "text-emerald-400";
  if (rate >= 70) return "text-amber-400";
  return "text-rose-400";
}

function successBarColor(rate: number | null): string {
  if (rate === null) return "bg-slate-600";
  if (rate >= 90) return "bg-emerald-500";
  if (rate >= 70) return "bg-amber-500";
  return "bg-rose-500";
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

function statusBadgeColor(status: string): string {
  const cfg = getStatusStyle(status);
  return `${cfg.text} ${cfg.bg} border-current/20`;
}

function formatFinishTime(isoString: string | null): string {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "UTC",
    }) + " UTC";
  } catch {
    return "—";
  }
}

function groupFailedTasks(tasks: DagTaskSummary[]): Record<string, DagTaskSummary[]> {
  const failed = tasks.filter(
    (t) => t.status === "failed" || t.status === "upstream_failed"
  );
  const groups: Record<string, DagTaskSummary[]> = {};
  for (const task of failed) {
    const key = task.task_group_id || "_ungrouped";
    if (!groups[key]) groups[key] = [];
    groups[key].push(task);
  }
  return groups;
}

interface DagCardProps {
  dag: DagSummary;
}

export const DagCard = memo(function DagCard({ dag }: DagCardProps) {
  const [showFailed, setShowFailed] = useState(false);

  const sortedTasks = [...dag.tasks].sort((a, b) => {
    const ai = STATUS_SEVERITY_ORDER.indexOf(a.status);
    const bi = STATUS_SEVERITY_ORDER.indexOf(b.status);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  const failedTotal = (dag.status_counts.failed ?? 0) + (dag.status_counts.upstream_failed ?? 0);
  const failedByGroup = failedTotal > 0 ? groupFailedTasks(dag.tasks) : {};
  const groupKeys = Object.keys(failedByGroup).sort((a, b) => {
    if (a === "_ungrouped") return 1;
    if (b === "_ungrouped") return -1;
    return a.localeCompare(b);
  });

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

      {/* Failed Tasks Panel (collapsible) */}
      {showFailed && failedTotal > 0 && (
        <div className="bg-rose-500/[0.04] border border-rose-500/10 rounded-xl p-3 flex flex-col gap-3">
          <div className="flex items-center gap-1.5">
            <AlertTriangle className="w-3 h-3 text-rose-500/70" />
            <span className="text-[9px] font-mono uppercase tracking-widest text-rose-500/70">
              {failedTotal} Failed Tasks
            </span>
          </div>
          {groupKeys.map((groupKey) => (
            <div key={groupKey} className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5 pl-0.5">
                <span className="w-2.5 h-px bg-slate-700/60" />
                <span className="text-[8px] font-mono uppercase tracking-[0.12em] text-slate-500">
                  {groupKey === "_ungrouped" ? "ungrouped" : formatGroupName(groupKey)}
                </span>
              </div>
              {failedByGroup[groupKey].map((task) => (
                <div
                  key={task.task_id}
                  className="flex items-center gap-3 py-1 px-2 rounded-md hover:bg-white/[0.02]"
                >
                  <span className="text-[11px] font-mono text-slate-300 truncate flex-1 min-w-0">
                    {task.pipeline_name || task.task_id}
                  </span>
                  <span
                    className={`text-[8px] font-mono uppercase tracking-widest px-1.5 py-px rounded border ${statusBadgeColor(task.status)}`}
                  >
                    {getStatusStyle(task.status).label.toLowerCase()}
                  </span>
                  <span className="text-[10px] font-mono text-slate-600 w-14 text-right shrink-0">
                    {task.latest_duration_seconds != null
                      ? formatDuration(task.latest_duration_seconds)
                      : "—"}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* Description */}
      {dag.description && (
        <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">
          {dag.description}
        </p>
      )}

      {/* Key Metrics Row */}
      <div className="flex items-center gap-4 text-[10px] font-mono text-slate-500">
        <span className="flex items-center gap-1">
          <Workflow className="w-3 h-3 text-slate-600" />
          {dag.task_count} tasks
        </span>
        <span className="text-white/10">|</span>
        <span className="flex items-center gap-1">
          <Layers className="w-3 h-3 text-slate-600" />
          {dag.pipeline_count} pipelines
        </span>
        {dag.schedule_interval && (
          <>
            <span className="text-white/10">|</span>
            <span className="flex items-center gap-1">
              <CalendarClock className="w-3 h-3 text-slate-600" />
              {dag.schedule_interval}
            </span>
          </>
        )}
      </div>

      {/* Duration Section */}
      <div className="bg-white/[0.02] rounded-xl p-3 flex flex-col gap-2">
        <div className="flex items-center gap-1.5 mb-0.5">
          <Timer className="w-3 h-3 text-slate-600" />
          <span className="text-[9px] font-mono uppercase tracking-widest text-slate-600">
            Duration
          </span>
        </div>
        {dag.avg_task_duration_seconds != null ? (
          <>
            <div className="flex items-end gap-2">
              <span className="text-xl font-semibold text-white font-mono tracking-tight">
                {formatDuration(dag.avg_task_duration_seconds)}
              </span>
              <span className="text-[10px] text-slate-500 font-mono uppercase mb-0.5">
                avg
              </span>
            </div>
            <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500">
              <span>
                min{" "}
                {dag.min_task_duration_seconds != null
                  ? formatDuration(dag.min_task_duration_seconds)
                  : "—"}
              </span>
              <span className="text-white/10">|</span>
              <span>
                max{" "}
                {dag.max_task_duration_seconds != null
                  ? formatDuration(dag.max_task_duration_seconds)
                  : "—"}
              </span>
              {dag.total_duration_seconds != null && (
                <>
                  <span className="text-white/10">|</span>
                  <span>
                    total {formatDuration(dag.total_duration_seconds)}
                  </span>
                </>
              )}
            </div>
          </>
        ) : (
          <span className="text-xs text-slate-600 font-mono">No run data</span>
        )}
      </div>

      {/* Success Rate */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <CheckCircle className="w-3 h-3 text-slate-600" />
            <span className="text-[9px] font-mono uppercase tracking-widest text-slate-600">
              Success Rate
            </span>
          </div>
          <span className={`text-sm font-mono font-semibold ${successRateColor(dag.success_rate)}`}>
            {dag.success_rate != null ? `${dag.success_rate}%` : "—"}
          </span>
        </div>
        <div className="relative h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className={`absolute inset-y-0 left-0 rounded-full transition-all duration-700 ${successBarColor(dag.success_rate)}`}
            style={{ width: `${Math.min(dag.success_rate ?? 0, 100)}%` }}
          />
        </div>
        <div className="flex items-center gap-3 text-[10px] font-mono text-slate-600 flex-wrap">
          {Object.entries(dag.status_counts)
            .sort(([a], [b]) => {
              const ai = STATUS_SEVERITY_ORDER.indexOf(a);
              const bi = STATUS_SEVERITY_ORDER.indexOf(b);
              return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
            })
            .map(([status, count]) => {
              if (count === 0) return null;
              const cfg = getStatusStyle(status);
              return (
                <span key={status} className={cfg.text}>
                  {count} {cfg.label.toLowerCase()}
                </span>
              );
            })}
        </div>
      </div>

      {/* Timing */}
      <div className="flex items-center gap-4 text-[10px] font-mono">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3 h-3 text-slate-600" />
          <span className="text-slate-500">Last finish</span>
          <span className="text-slate-300">
            {formatFinishTime(dag.latest_run_end)}
          </span>
        </div>
        {dag.typical_finish_hour && (
          <>
            <span className="text-white/10">|</span>
            <span className="text-slate-500">Typical</span>
            <span className="text-indigo-400">{dag.typical_finish_hour}</span>
          </>
        )}
      </div>

      {/* 30d History */}
      {dag.total_runs_30d > 0 && (
        <div className="flex items-center gap-3 text-[10px] font-mono text-slate-600">
          <span>{dag.total_runs_30d} runs ({dag.period_label ?? "30d"})</span>
          {dag.dag_success_rate_30d != null && (
            <>
              <span className="text-white/10">|</span>
              <span className={successRateColor(dag.dag_success_rate_30d)}>
                {dag.dag_success_rate_30d}% task success
              </span>
            </>
          )}
        </div>
      )}

      {/* Task Status Dots */}
      <div className="pt-2 border-t border-white/5">
        <div className="flex items-center gap-1.5 mb-2">
          <span className="text-[9px] font-mono uppercase tracking-widest text-slate-600">
            Tasks
          </span>
        </div>
        <TaskStatusDots tasks={sortedTasks} />
      </div>
    </div>
  );
});
