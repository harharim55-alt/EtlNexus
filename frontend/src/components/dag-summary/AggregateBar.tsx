import { Activity, CheckCircle, Layers, Timer, Workflow } from "lucide-react";
import type { DagSummaryAggregate } from "@/types/dag-summary";

function rateColor(rate: number | null): string {
  if (rate === null) return "text-text-muted";
  if (rate >= 90) return "text-emerald-400";
  if (rate >= 70) return "text-amber-400";
  return "text-rose-400";
}

interface AggregateBarProps {
  aggregate: DagSummaryAggregate;
}

export function AggregateBar({ aggregate }: AggregateBarProps) {
  const tiles = [
    {
      icon: Workflow,
      label: "Total DAGs",
      value: String(aggregate.total_dags),
      sub: null,
      color: "text-foreground",
    },
    {
      icon: Activity,
      label: "Active",
      value: String(aggregate.active_dags),
      sub: aggregate.total_dags - aggregate.active_dags > 0
        ? `${aggregate.total_dags - aggregate.active_dags} paused`
        : null,
      color: "text-emerald-400",
    },
    {
      icon: Layers,
      label: "Pipelines",
      value: String(aggregate.total_pipelines),
      sub: null,
      color: "text-indigo-400",
    },
    {
      icon: CheckCircle,
      label: "Success Rate",
      value: aggregate.overall_success_rate != null
        ? `${aggregate.overall_success_rate}%`
        : "—",
      sub: null,
      color: rateColor(aggregate.overall_success_rate),
    },
    {
      icon: Timer,
      label: `Runs (${aggregate.period_label ?? "30d"})`,
      value: String(aggregate.total_runs_30d),
      sub: null,
      color: "text-foreground",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {tiles.map((tile) => {
        const Icon = tile.icon;
        return (
          <div
            key={tile.label}
            className="bg-card border border-border rounded-2xl p-4 flex flex-col gap-2"
          >
            <div className="flex items-center gap-1.5">
              <Icon className="w-3 h-3 text-text-faint" />
              <span className="text-[9px] font-mono uppercase tracking-widest text-text-faint">
                {tile.label}
              </span>
            </div>
            <span className={`text-2xl font-semibold font-mono tracking-tight ${tile.color}`}>
              {tile.value}
            </span>
            {tile.sub && (
              <span className="text-[10px] font-mono text-text-faint">
                {tile.sub}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
