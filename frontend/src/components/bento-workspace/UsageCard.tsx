import { Activity, Workflow, Globe } from "lucide-react";
import { usePipelineUsage } from "@/hooks/use-pipeline-usage";
import { Skeleton } from "@/components/ui/skeleton";
import type { PipelineUsage } from "@/types/usage";

interface UsageCardProps {
  etlName: string;
}

const STATUS_DOT: Record<string, string> = {
  success: "bg-emerald-400",
  failed: "bg-red-400",
  running: "bg-amber-400 animate-pulse",
  unknown: "bg-slate-500",
};

const STATUS_GLOW: Record<string, string> = {
  success: "shadow-[0_0_8px_rgba(52,211,153,0.5)]",
  failed: "shadow-[0_0_8px_rgba(248,113,113,0.5)]",
  running: "shadow-[0_0_8px_rgba(251,191,36,0.5)]",
  unknown: "",
};

function formatAccessCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 1_000) return `${(count / 1000).toFixed(1)}k`;
  return count.toString();
}

function UsageRow({ usage }: { usage: PipelineUsage }) {
  const TypeIcon = usage.usage_type === "api" ? Globe : Workflow;
  const typeLabel = usage.usage_type === "api" ? "API" : "ETL";
  const statusDot = STATUS_DOT[usage.airflow_status ?? "unknown"] ?? STATUS_DOT.unknown;
  const statusGlow = STATUS_GLOW[usage.airflow_status ?? "unknown"] ?? "";

  return (
    <div
      className={`group flex items-center gap-3 px-4 py-3 transition-all duration-200 ${
        usage.is_current
          ? "bg-indigo-500/[0.06] border-b border-indigo-500/20"
          : "hover:bg-white/[0.03]"
      }`}
    >
      {/* Status dot */}
      <div
        className={`w-2 h-2 rounded-full shrink-0 transition-transform duration-200 group-hover:scale-125 ${statusDot} ${statusGlow}`}
      />

      {/* Name + type badge */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className={`text-sm font-medium truncate transition-colors ${
              usage.is_current
                ? "text-indigo-300"
                : "text-slate-200 group-hover:text-white"
            }`}
          >
            {usage.consumer_name}
          </span>
          <span
            className={`inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 border border-white/5 shrink-0 ${
              usage.usage_type === "api" ? "text-violet-400" : "text-cyan-400"
            }`}
          >
            <TypeIcon className="w-2.5 h-2.5" />
            {typeLabel}
          </span>
          {usage.is_current && (
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shrink-0">
              current
            </span>
          )}
        </div>
        {usage.description && !usage.is_current && (
          <p className="text-[11px] text-slate-500 mt-0.5 truncate">
            {usage.description}
          </p>
        )}
      </div>

      {/* Network (DAG) */}
      {usage.dag_id && (
        <span className="text-[10px] font-mono px-2 py-1 rounded bg-white/[0.03] border border-white/5 text-slate-400 shrink-0 max-w-[140px] truncate">
          {usage.dag_id}
        </span>
      )}

      {/* Reads count */}
      <div className="text-right shrink-0 w-14">
        <div className={`text-xs font-mono tabular-nums ${usage.is_current ? "text-indigo-400" : "text-slate-300"}`}>
          {formatAccessCount(usage.access_count)}
        </div>
        <div className="text-[9px] text-slate-600 font-mono">reads</div>
      </div>
    </div>
  );
}

export function UsageCard({ etlName }: UsageCardProps) {
  const { data, isLoading } = usePipelineUsage(etlName);
  const usages = data?.usages ?? [];
  const consumers = usages.filter((u) => !u.is_current);

  return (
    <div className="col-span-12 bg-[#18181b] border border-white/5 rounded-2xl flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-white/5 bg-[#18181b]/50 backdrop-blur flex items-center justify-between">
        <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
          <Activity className="w-3.5 h-3.5" /> Consumers & Usage
        </h3>
        {!isLoading && consumers.length > 0 && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-400">
            {consumers.length} downstream
          </span>
        )}
      </div>

      {/* Content */}
      <div>
        {isLoading ? (
          <div className="space-y-2 p-4">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full bg-white/5 rounded-xl" />
            ))}
          </div>
        ) : usages.length > 0 ? (
          <div className="divide-y divide-white/[0.02]">
            {usages.map((usage) => (
              <UsageRow key={usage.id + (usage.is_current ? "-current" : "")} usage={usage} />
            ))}
          </div>
        ) : (
          <div className="text-center text-slate-600 text-xs py-8 font-mono">
            No consumers tracked
          </div>
        )}
      </div>
    </div>
  );
}
