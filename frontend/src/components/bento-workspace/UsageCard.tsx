import { Activity, LayoutDashboard, Download, GitBranch, Database, Workflow } from "lucide-react";
import { usePipelineUsage } from "@/hooks/use-pipeline-usage";
import { Skeleton } from "@/components/ui/skeleton";
import type { PipelineUsage } from "@/types/usage";

interface UsageCardProps {
  pipelineId: string;
}

const TYPE_CONFIG: Record<string, { icon: typeof Activity; label: string; color: string }> = {
  etl: { icon: Workflow, label: "ETL", color: "text-cyan-400" },
  dashboard: { icon: LayoutDashboard, label: "Dashboard", color: "text-amber-400" },
  import: { icon: Download, label: "Import", color: "text-emerald-400" },
  downstream: { icon: GitBranch, label: "Downstream", color: "text-indigo-400" },
  catalog_query: { icon: Database, label: "Catalog", color: "text-pink-400" },
};

const STATUS_DOT: Record<string, string> = {
  success: "bg-emerald-400",
  failed: "bg-red-400",
  running: "bg-amber-400",
  unknown: "bg-slate-500",
};

function formatAccessCount(count: number): string {
  if (count >= 1_000) return `${(count / 1000).toFixed(1)}k`;
  return count.toString();
}

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffHours < 1) return "Just now";
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

function getIntensityClass(count: number, maxCount: number): string {
  const ratio = maxCount > 0 ? count / maxCount : 0;
  if (ratio > 0.7) return "bg-indigo-500";
  if (ratio > 0.3) return "bg-indigo-500/60";
  return "bg-indigo-500/25";
}

function UsageRow({ usage, maxCount }: { usage: PipelineUsage; maxCount: number }) {
  const config = TYPE_CONFIG[usage.usage_type] || TYPE_CONFIG.import;
  const Icon = config.icon;
  const isEtl = !!usage.airflow_status;

  return (
    <div className="group flex items-center gap-3 px-4 py-2.5 rounded-xl hover:bg-white/[0.03] transition-all duration-200">
      {/* Status/intensity dot */}
      <div
        className={`w-2 h-2 rounded-full shrink-0 transition-transform duration-200 group-hover:scale-125 ${
          isEtl
            ? STATUS_DOT[usage.airflow_status!] || STATUS_DOT.unknown
            : getIntensityClass(usage.access_count, maxCount)
        }`}
      />

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-200 font-medium truncate group-hover:text-white transition-colors">
            {usage.consumer_name}
          </span>
          <span className={`inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 border border-white/5 ${config.color}`}>
            <Icon className="w-2.5 h-2.5" />
            {config.label}
          </span>
        </div>
        {usage.description && (
          <p className="text-[11px] text-slate-500 mt-0.5 truncate">
            {usage.description}
          </p>
        )}
      </div>

      {/* Right side: airflow status or hit count */}
      <div className="flex items-center gap-4 shrink-0">
        {isEtl ? (
          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 border border-white/5 ${
            usage.airflow_status === "success" ? "text-emerald-400"
            : usage.airflow_status === "failed" ? "text-red-400"
            : usage.airflow_status === "running" ? "text-amber-400"
            : "text-slate-500"
          }`}>
            {usage.airflow_status}
          </span>
        ) : (
          <div className="text-right">
            <div className="text-xs font-mono text-slate-300 tabular-nums">
              {formatAccessCount(usage.access_count)}
            </div>
            <div className="text-[9px] text-slate-600 font-mono uppercase">hits</div>
          </div>
        )}
        <div className="w-px h-6 bg-white/5" />
        <div className="text-[10px] text-slate-500 font-mono w-16 text-right">
          {formatRelativeTime(usage.last_accessed_at)}
        </div>
      </div>
    </div>
  );
}

export function UsageCard({ pipelineId }: UsageCardProps) {
  const { data, isLoading } = usePipelineUsage(pipelineId);
  const usages = data?.usages ?? [];
  const maxCount = Math.max(...usages.filter((u) => !u.airflow_status).map((u) => u.access_count), 1);

  const typeCounts = usages.reduce<Record<string, number>>((acc, u) => {
    acc[u.usage_type] = (acc[u.usage_type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="col-span-12 lg:col-span-7 bg-[#18181b] border border-white/5 rounded-2xl flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-white/5 bg-[#18181b]/50 backdrop-blur flex items-center justify-between">
        <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
          <Activity className="w-3.5 h-3.5" /> Consumers & Usage
        </h3>
        {!isLoading && usages.length > 0 && (
          <div className="flex items-center gap-2">
            {Object.entries(typeCounts).map(([type, count]) => {
              const config = TYPE_CONFIG[type] || TYPE_CONFIG.import;
              return (
                <span
                  key={type}
                  className={`text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 ${config.color}`}
                >
                  {count} {config.label.toLowerCase()}
                </span>
              );
            })}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-2">
        {isLoading ? (
          <div className="space-y-2 p-3">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full bg-white/5 rounded-xl" />
            ))}
          </div>
        ) : usages.length > 0 ? (
          <div className="divide-y divide-white/[0.02]">
            {usages.map((usage) => (
              <UsageRow key={usage.id} usage={usage} maxCount={maxCount} />
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
