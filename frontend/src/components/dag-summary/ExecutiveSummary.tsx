import { Activity, CheckCircle, Clock, Database } from "lucide-react";
import { formatDuration } from "@/lib/format";
import type { DagSummaryAggregate, DagSummary } from "@/types/dag-summary";

/* ── Helpers ────────────────────────────────────────────────────────── */

function rateColorClass(rate: number | null): string {
  if (rate === null) return "text-text-muted";
  if (rate >= 90) return "text-emerald-400";
  if (rate >= 70) return "text-amber-400";
  return "text-rose-400";
}

function rateBgClass(rate: number | null): string {
  if (rate === null) return "bg-slate-500/10 border-slate-500/20";
  if (rate >= 90) return "bg-emerald-500/10 border-emerald-500/20";
  if (rate >= 70) return "bg-amber-500/10 border-amber-500/20";
  return "bg-rose-500/10 border-rose-500/20";
}

function rateIconColor(rate: number | null): string {
  if (rate === null) return "text-text-faint";
  if (rate >= 90) return "text-emerald-400";
  if (rate >= 70) return "text-amber-400";
  return "text-rose-400";
}

/* ── Props ──────────────────────────────────────────────────────────── */

interface ExecutiveSummaryProps {
  aggregate: DagSummaryAggregate;
  dags: DagSummary[];
}

/* ── Component ──────────────────────────────────────────────────────── */

export function ExecutiveSummary({ aggregate, dags }: ExecutiveSummaryProps) {
  const activeDags = dags.filter((d) => !d.is_paused).length;

  // Compute average duration across all DAGs that have a value
  const durations = dags
    .map((d) => d.avg_task_duration_seconds)
    .filter((v): v is number => v != null);
  const avgDuration =
    durations.length > 0
      ? durations.reduce((sum, v) => sum + v, 0) / durations.length
      : null;

  const kpis = [
    {
      label: "Total Active",
      value: String(activeDags),
      icon: Activity,
      iconBg: "bg-indigo-500/10 border-indigo-500/20",
      iconColor: "text-indigo-400",
      valueColor: "text-indigo-400",
    },
    {
      label: "Overall Success Rate",
      value:
        aggregate.overall_success_rate != null
          ? `${aggregate.overall_success_rate}%`
          : "\u2014",
      icon: CheckCircle,
      iconBg: rateBgClass(aggregate.overall_success_rate),
      iconColor: rateIconColor(aggregate.overall_success_rate),
      valueColor: rateColorClass(aggregate.overall_success_rate),
    },
    {
      label: "Avg Duration",
      value: avgDuration != null ? formatDuration(avgDuration) : "\u2014",
      icon: Clock,
      iconBg: "bg-sky-500/10 border-sky-500/20",
      iconColor: "text-sky-400",
      valueColor: "text-sky-400",
    },
    {
      label: "Pipeline Coverage",
      value: String(aggregate.total_pipelines),
      icon: Database,
      iconBg: "bg-violet-500/10 border-violet-500/20",
      iconColor: "text-violet-400",
      valueColor: "text-violet-400",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {kpis.map((kpi) => {
        const Icon = kpi.icon;
        return (
          <div
            key={kpi.label}
            className="bg-card border border-border rounded-xl p-4 flex flex-col gap-3"
          >
            <div className="flex items-center gap-2">
              <div
                className={`size-7 ${kpi.iconBg} border rounded-lg flex items-center justify-center`}
              >
                <Icon className={`size-3.5 ${kpi.iconColor}`} />
              </div>
              <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted">
                {kpi.label}
              </span>
            </div>
            <span
              className={`text-2xl font-semibold font-mono tracking-tight ${kpi.valueColor}`}
            >
              {kpi.value}
            </span>
          </div>
        );
      })}
    </div>
  );
}
