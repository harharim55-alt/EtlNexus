import { useState } from "react";
import { Gauge, Clock, Cpu, Server, TrendingUp } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { useResourceMetrics } from "@/hooks/use-resource-metrics";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useRunSelectorStore } from "@/stores/run-selector-store";
import { computeRunStats, recomputeCapacityBars } from "./resource-performance/resource-utils";
import {
  DurationSection,
  ResourceSection,
  CapacitySection,
  SparkInternalsSection,
} from "./resource-performance/ResourceSections";
import { ResourceHistoryModal } from "./ResourceHistoryModal";

interface ResourcePerformanceCardProps {
  pipelineId: string;
}

// --- Main Card ---
export function ResourcePerformanceCard({ pipelineId }: ResourcePerformanceCardProps) {
  const { data, isLoading } = useResourceMetrics(pipelineId);
  const selectedDagId = usePipelineStore((s) => s.selectedDagId);
  const _dagRunId = useRunSelectorStore((s) => s.selectedDagRunId);
  const [historyOpen, setHistoryOpen] = useState(false);
  void _dagRunId; // Will power per-run resource view in next iteration

  return (
    <div className="col-span-12 bg-[#18181b] border border-white/5 rounded-2xl p-5 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Gauge className="w-3.5 h-3.5 text-slate-500" />
          <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500">
            Resource & Performance
          </h3>
        </div>
          <button
            type="button"
            onClick={() => setHistoryOpen(true)}
            className="text-[9px] font-mono px-2 py-1 rounded border transition-all cursor-pointer text-slate-500 bg-white/[0.03] border-white/5 hover:border-indigo-500/30 hover:text-indigo-400 hover:bg-indigo-500/10 flex items-center gap-1.5"
          >
            <TrendingUp className="w-3 h-3" />
            Usage Over Time
          </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-3 gap-6">
          <Skeleton className="h-32 bg-white/5 rounded-xl" />
          <Skeleton className="h-32 bg-white/5 rounded-xl" />
          <Skeleton className="h-32 bg-white/5 rounded-xl" />
        </div>
      ) : data ? (
        (() => {
          const filteredConfigs = selectedDagId
            ? data.resource_configs.filter((c) => c.dag_id === selectedDagId)
            : data.resource_configs;
          const filteredRuns = selectedDagId
            ? data.recent_runs.filter((r) => r.dag_id === selectedDagId)
            : data.recent_runs;
          const stats = selectedDagId ? computeRunStats(filteredRuns) : null;
          const filteredCapacity = selectedDagId && filteredConfigs.length > 0
            ? recomputeCapacityBars(filteredConfigs, data.capacity)
            : data.capacity;
          return (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Duration */}
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5 mb-3">
                  <Clock className="w-3 h-3 text-slate-600" />
                  <span className="text-[9px] font-mono uppercase tracking-widest text-slate-600">
                    Run Duration
                  </span>
                </div>
                <DurationSection
                  avgDuration={stats ? stats.avg : data.avg_duration_seconds}
                  minDuration={stats ? stats.min : data.min_duration_seconds}
                  maxDuration={stats ? stats.max : data.max_duration_seconds}
                  runCount={stats ? stats.count : data.run_count}
                  successRate={stats ? stats.successRate : data.success_rate}
                  recentRuns={filteredRuns}
                />
              </div>

              {/* Resources */}
              <div className="lg:border-l lg:border-white/5 lg:-my-1 lg:pl-6">
                <div className="flex items-center gap-1.5 mb-3">
                  <Cpu className="w-3 h-3 text-slate-600" />
                  <span className="text-[9px] font-mono uppercase tracking-widest text-slate-600">
                    Resources
                  </span>
                </div>
                <ResourceSection
                  configs={filteredConfigs}
                  actualUsage={data.actual_usage}
                />
                <SparkInternalsSection actualUsage={data.actual_usage} />
              </div>

              {/* Capacity */}
              <div className="lg:border-l lg:border-white/5 lg:-my-1 lg:pl-6">
                <div className="flex items-center gap-1.5 mb-3">
                  <Server className="w-3 h-3 text-slate-600" />
                  <span className="text-[9px] font-mono uppercase tracking-widest text-slate-600">
                    Cluster Capacity
                  </span>
                </div>
                <CapacitySection bars={filteredCapacity} />
              </div>
            </div>
          );
        })()
      ) : (
        <div className="flex items-center justify-center py-8">
          <span className="text-xs text-slate-600 font-mono">
            No resource data available
          </span>
        </div>
      )}

      <ResourceHistoryModal
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        pipelineId={pipelineId}
      />
    </div>
  );
}
