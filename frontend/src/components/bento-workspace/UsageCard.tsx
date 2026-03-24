import { useState, useRef, useEffect } from "react";
import { Activity, Workflow, Globe, Network, ChevronDown } from "lucide-react";
import { usePipelineUsage } from "@/hooks/use-pipeline-usage";
import { Skeleton } from "@/components/ui/skeleton";
import { getStatusStyle } from "@/lib/status-config";
import { DateRangePicker } from "@/components/shared/DateRangePicker";
import type { PipelineUsage } from "@/types/usage";

interface UsageCardProps {
  etlName: string;
}

function formatCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 1_000) return `${(count / 1000).toFixed(1)}k`;
  return count.toString();
}

function UsageRow({ usage }: { usage: PipelineUsage }) {
  const TypeIcon = usage.usage_type === "api" ? Globe : Workflow;
  const typeLabel = usage.usage_type === "api" ? "API" : "ETL";
  const cfg = getStatusStyle(usage.airflow_status ?? "unknown");

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
        className={`w-2 h-2 rounded-full shrink-0 transition-transform duration-200 group-hover:scale-125 ${cfg.dot} ${cfg.glow}`}
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

      {/* Reads metrics */}
      <div className="text-right shrink-0 w-20">
        <div className={`text-xs font-mono tabular-nums ${usage.is_current ? "text-indigo-400" : "text-slate-300"}`}>
          {formatCount(usage.unique_reads)}
        </div>
        <div className="text-[9px] text-slate-600 font-mono">unique</div>
      </div>
      <div className="text-right shrink-0 w-16">
        <div className={`text-xs font-mono tabular-nums ${usage.is_current ? "text-indigo-400/70" : "text-slate-400"}`}>
          {formatCount(usage.total_reads)}
        </div>
        <div className="text-[9px] text-slate-600 font-mono">total</div>
      </div>
    </div>
  );
}

export function UsageCard({ etlName }: UsageCardProps) {
  const [selectedNetwork, setSelectedNetwork] = useState<string | null>(null);
  const [networkOpen, setNetworkOpen] = useState(false);
  const networkRef = useRef<HTMLDivElement>(null);
  const { data, isLoading } = usePipelineUsage(etlName, selectedNetwork);
  const usages = data?.usages ?? [];
  const consumers = usages.filter((u) => !u.is_current);

  // Extract unique networks from all usages (before filtering) for the dropdown
  const networks = [...new Set(usages.map((u) => u.dag_id).filter(Boolean))] as string[];

  // Close network dropdown on outside click
  useEffect(() => {
    if (!networkOpen) return;
    function handleClick(e: MouseEvent) {
      if (networkRef.current && !networkRef.current.contains(e.target as Node)) {
        setNetworkOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [networkOpen]);

  const networkLabel = selectedNetwork ?? "All Networks";
  const isFiltered = selectedNetwork !== null;

  return (
    <div className="bg-[#18181b] border border-white/5 rounded-2xl flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-white/5 bg-[#18181b]/50 backdrop-blur flex items-center justify-between">
        <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
          <Activity className="w-3.5 h-3.5" /> Consumers & Usage
        </h3>
        <div className="flex items-center gap-2">
          {!isLoading && consumers.length > 0 && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-400">
              {consumers.length} downstream
            </span>
          )}
          {/* Network filter */}
          {networks.length > 1 && (
            <div className="relative" ref={networkRef}>
              <button
                type="button"
                onClick={() => setNetworkOpen(!networkOpen)}
                className={`inline-flex items-center gap-1.5 text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer ${
                  isFiltered
                    ? "text-indigo-300 bg-indigo-500/15 border-indigo-500/30 shadow-[0_0_8px_rgba(99,102,241,0.12)]"
                    : "text-slate-500 bg-white/[0.02] border-white/5 hover:border-white/15 hover:text-slate-400"
                }`}
              >
                <Network className="w-2.5 h-2.5" />
                {networkLabel}
                <ChevronDown className={`w-2.5 h-2.5 transition-transform ${networkOpen ? "rotate-180" : ""}`} />
              </button>
              {networkOpen && (
                <div className="absolute top-full right-0 mt-2 z-50 bg-[#18181b] border border-white/10 rounded-xl py-1 shadow-xl min-w-[160px]">
                  <button
                    type="button"
                    onClick={() => { setSelectedNetwork(null); setNetworkOpen(false); }}
                    className={`w-full text-left text-[10px] font-mono px-3 py-1.5 transition-colors cursor-pointer ${
                      !isFiltered
                        ? "text-indigo-300 bg-indigo-500/10"
                        : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                    }`}
                  >
                    All Networks
                  </button>
                  {networks.map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => { setSelectedNetwork(n); setNetworkOpen(false); }}
                      className={`w-full text-left text-[10px] font-mono px-3 py-1.5 transition-colors cursor-pointer ${
                        selectedNetwork === n
                          ? "text-indigo-300 bg-indigo-500/10"
                          : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                      }`}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          <DateRangePicker />
        </div>
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
