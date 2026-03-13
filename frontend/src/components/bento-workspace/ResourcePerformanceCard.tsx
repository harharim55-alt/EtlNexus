import { Gauge, HardDrive, Cpu, Server, MemoryStick, Clock, CheckCircle, Activity, ArrowDownUp, Database } from "lucide-react";
import { DateRangePicker } from "@/components/shared/DateRangePicker";
import { Skeleton } from "@/components/ui/skeleton";
import { useResourceMetrics } from "@/hooks/use-resource-metrics";
import { usePipelineStore } from "@/stores/pipeline-store";
import type { ActualUsage, CapacityBar as CapacityBarType, DurationRun, ResourceConfigEntry } from "@/types/resources";

interface ResourcePerformanceCardProps {
  pipelineId: string;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins < 60) return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  const hrs = Math.floor(mins / 60);
  const remainMins = mins % 60;
  return remainMins > 0 ? `${hrs}h ${remainMins}m` : `${hrs}h`;
}

function statusColor(status: string): string {
  switch (status) {
    case "success": return "bg-emerald-500";
    case "failed": return "bg-rose-500";
    case "running": return "bg-amber-500";
    default: return "bg-slate-600";
  }
}

function capacityColor(pct: number): string {
  if (pct >= 80) return "bg-rose-500";
  if (pct >= 60) return "bg-amber-500";
  return "bg-emerald-500";
}

function capacityTextColor(pct: number): string {
  if (pct >= 80) return "text-rose-400";
  if (pct >= 60) return "text-amber-400";
  return "text-emerald-400";
}

// --- Duration Section ---
function DurationSection({
  avgDuration,
  minDuration,
  maxDuration,
  runCount,
  successRate,
  recentRuns,
}: {
  avgDuration: number | null;
  minDuration: number | null;
  maxDuration: number | null;
  runCount: number;
  successRate: number | null;
  recentRuns: DurationRun[];
}) {
  if (runCount === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-xs text-slate-600 font-mono">No run history</span>
      </div>
    );
  }

  const maxBarDuration = Math.max(...recentRuns.map((r) => r.duration_seconds), 1);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-end gap-2">
        <span className="text-2xl font-semibold text-white font-mono tracking-tight">
          {avgDuration != null ? formatDuration(avgDuration) : "—"}
        </span>
        <span className="text-[10px] text-slate-500 font-mono uppercase mb-1">avg</span>
      </div>
      <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500">
        <span>
          min {minDuration != null ? formatDuration(minDuration) : "—"}
        </span>
        <span className="text-white/10">|</span>
        <span>
          max {maxDuration != null ? formatDuration(maxDuration) : "—"}
        </span>
        <span className="text-white/10">|</span>
        <span>{runCount} runs</span>
      </div>
      {successRate != null && (
        <div className="flex items-center gap-1.5">
          <CheckCircle className="w-3 h-3 text-emerald-500" />
          <span className="text-[10px] font-mono text-slate-400">
            {successRate}% success rate
          </span>
        </div>
      )}
      {/* Mini run sparkline */}
      <div className="flex items-end gap-[3px] h-8 mt-1">
        {recentRuns
          .slice()
          .reverse()
          .slice(-12)
          .map((run, i) => {
            const height = Math.max((run.duration_seconds / maxBarDuration) * 100, 8);
            return (
              <div
                key={i}
                className={`rounded-sm w-[6px] ${statusColor(run.status)} opacity-80 hover:opacity-100 transition-opacity`}
                style={{ height: `${height}%` }}
                title={`${formatDuration(run.duration_seconds)} — ${run.status} (${run.dag_id})`}
              />
            );
          })}
      </div>
    </div>
  );
}

// --- Resource Config Section ---
const RESOURCE_ICONS = {
  driver: HardDrive,
  executor: MemoryStick,
  cores: Cpu,
  executors: Server,
} as const;

function ResourceSection({
  configs,
  actualUsage,
}: {
  configs: ResourceConfigEntry[];
  actualUsage: ActualUsage;
}) {
  if (configs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-xs text-slate-600 font-mono">No Spark resources</span>
      </div>
    );
  }

  const config = configs.find((c) => !c.is_dag_override) || configs[0];

  const items = [
    {
      key: "driver" as const,
      label: "Driver Memory",
      allocated: config.spark_driver_memory,
      actual: actualUsage.avg_driver_memory_used_mb
        ? `~${(actualUsage.avg_driver_memory_used_mb / 1024).toFixed(1)}g`
        : null,
    },
    {
      key: "executor" as const,
      label: "Executor Memory",
      allocated: config.spark_executor_memory,
      actual: actualUsage.avg_executor_memory_peak_mb
        ? `~${(actualUsage.avg_executor_memory_peak_mb / 1024).toFixed(1)}g`
        : null,
    },
    {
      key: "cores" as const,
      label: "CPU Cores",
      allocated: config.spark_executor_cores?.toString() ?? null,
      actual: actualUsage.avg_cpu_utilization_pct
        ? `${actualUsage.avg_cpu_utilization_pct.toFixed(0)}% util`
        : null,
    },
    {
      key: "executors" as const,
      label: "Executors",
      allocated: config.spark_num_executors?.toString() ?? null,
      actual: actualUsage.avg_executors_active
        ? `~${actualUsage.avg_executors_active}`
        : null,
    },
  ];

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3">
        {items.map((item) => {
          if (!item.allocated) return null;
          const Icon = RESOURCE_ICONS[item.key];
          return (
            <div key={item.key} className="flex items-start gap-2">
              <Icon className="w-3.5 h-3.5 text-slate-600 mt-0.5 shrink-0" />
              <div className="min-w-0">
                <div className="text-[9px] font-mono uppercase tracking-widest text-slate-600">
                  {item.label}
                </div>
                <div className="text-sm font-medium text-white font-mono">
                  {item.allocated}
                </div>
                {item.actual && (
                  <div className="text-[10px] font-mono text-indigo-400">
                    {item.actual}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// --- Capacity Section ---
function CapacitySection({ bars }: { bars: CapacityBarType[] }) {
  if (bars.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-xs text-slate-600 font-mono">No capacity data</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {bars.map((bar) => (
        <div key={bar.label} className="flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono uppercase tracking-widest text-slate-600">
              {bar.label}
            </span>
            <span className={`text-[10px] font-mono ${capacityTextColor(bar.allocated_pct)}`}>
              {Math.round(bar.allocated_pct)}%
            </span>
          </div>
          {/* Stacked bar: used (solid) + allocated (lighter) within capacity track */}
          <div className="relative h-2 bg-white/5 rounded-full overflow-hidden">
            {/* Allocated fill (lighter) */}
            <div
              className="absolute inset-y-0 left-0 bg-white/10 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(bar.allocated_pct, 100)}%` }}
            />
            {/* Used fill (solid, on top) */}
            {bar.used !== "—" && bar.used_pct > 0 && (
              <div
                className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${capacityColor(bar.used_pct)}`}
                style={{ width: `${Math.min(bar.used_pct, 100)}%` }}
              />
            )}
          </div>
          <div className="text-[9px] font-mono text-slate-500">
            {bar.used !== "—" ? (
              <>
                <span className="text-slate-400">{bar.used}</span>
                {" used / "}
                {bar.allocated}
                {" alloc / "}
                {bar.max_capacity}
              </>
            ) : (
              <>
                {bar.allocated}
                {" alloc / "}
                {bar.max_capacity}
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function formatBytes(bytes: number | null): string {
  if (bytes == null || bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(1024));
  const idx = Math.min(i, units.length - 1);
  return `${(bytes / Math.pow(1024, idx)).toFixed(idx > 1 ? 1 : 0)} ${units[idx]}`;
}

function formatMs(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60_000).toFixed(1)}m`;
}

function MetricsSourceBadge({ source }: { source: string | null }) {
  if (!source) return null;
  const isReal = source !== "simulation";
  return (
    <span
      className={`ml-2 text-[8px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-full ${
        isReal
          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
          : "bg-slate-500/10 text-slate-500 border border-slate-500/20"
      }`}
    >
      {isReal ? "Real" : "Simulated"}
    </span>
  );
}

// --- Spark Internals Section (sparkMeasure metrics) ---
function SparkInternalsSection({ actualUsage }: { actualUsage: ActualUsage }) {
  const hasData =
    actualUsage.metrics_source != null &&
    actualUsage.metrics_source !== "simulation" &&
    (actualUsage.avg_jvm_gc_time_ms != null ||
      actualUsage.avg_shuffle_read_bytes != null ||
      actualUsage.avg_input_bytes != null);

  if (!hasData) return null;

  const items = [
    {
      icon: Activity,
      label: "GC Time",
      value: formatMs(actualUsage.avg_jvm_gc_time_ms),
      warn: (actualUsage.avg_jvm_gc_time_ms ?? 0) > 10_000,
    },
    {
      icon: ArrowDownUp,
      label: "Shuffle Read",
      value: formatBytes(actualUsage.avg_shuffle_read_bytes),
    },
    {
      icon: ArrowDownUp,
      label: "Shuffle Write",
      value: formatBytes(actualUsage.avg_shuffle_write_bytes),
    },
    {
      icon: Database,
      label: "Input",
      value: formatBytes(actualUsage.avg_input_bytes),
    },
    {
      icon: Database,
      label: "Output",
      value: formatBytes(actualUsage.avg_output_bytes),
    },
    {
      icon: HardDrive,
      label: "Mem Spill",
      value: formatBytes(actualUsage.avg_memory_bytes_spilled),
      warn: (actualUsage.avg_memory_bytes_spilled ?? 0) > 0,
    },
    {
      icon: HardDrive,
      label: "Disk Spill",
      value: formatBytes(actualUsage.avg_disk_bytes_spilled),
      warn: (actualUsage.avg_disk_bytes_spilled ?? 0) > 0,
    },
    {
      icon: MemoryStick,
      label: "Peak Exec Mem",
      value: formatBytes(actualUsage.avg_peak_execution_memory),
    },
  ].filter((item) => item.value !== "0 B" && item.value !== "—");

  if (items.length === 0) return null;

  return (
    <div className="mt-4 pt-3 border-t border-white/5">
      <div className="flex items-center gap-1.5 mb-2.5">
        <Activity className="w-3 h-3 text-slate-600" />
        <span className="text-[9px] font-mono uppercase tracking-widest text-slate-600">
          Spark Internals
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="flex items-start gap-1.5">
              <Icon className={`w-3 h-3 mt-0.5 shrink-0 ${item.warn ? "text-amber-500" : "text-slate-600"}`} />
              <div className="min-w-0">
                <div className="text-[8px] font-mono uppercase tracking-widest text-slate-600 truncate">
                  {item.label}
                </div>
                <div className={`text-xs font-mono ${item.warn ? "text-amber-400" : "text-white"}`}>
                  {item.value}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function parseMemoryGb(mem: string): number {
  const match = mem.trim().match(/^(\d+(?:\.\d+)?)\s*([gmtGMT]?)$/);
  if (!match) return 0;
  const val = parseFloat(match[1]);
  const unit = match[2].toLowerCase();
  if (unit === "m") return val / 1024;
  if (unit === "t") return val * 1024;
  return val;
}

function recomputeCapacityBars(
  configs: ResourceConfigEntry[],
  originalBars: CapacityBarType[],
): CapacityBarType[] {
  if (configs.length === 0 || originalBars.length === 0) return originalBars;

  const config = configs.find((c) => !c.is_dag_override) || configs[0];

  // Build a lookup from original bars for max_capacity + used values
  const barMap = new Map(originalBars.map((b) => [b.label, b]));

  const result: CapacityBarType[] = [];

  const driverBar = barMap.get("Driver Memory");
  if (driverBar && config.spark_driver_memory) {
    const allocGb = parseMemoryGb(config.spark_driver_memory);
    const maxGb = parseMemoryGb(driverBar.max_capacity);
    result.push({
      ...driverBar,
      allocated: config.spark_driver_memory,
      allocated_pct: maxGb ? Math.round((allocGb / maxGb) * 1000) / 10 : 0,
    });
  } else if (driverBar) {
    result.push(driverBar);
  }

  const execMemBar = barMap.get("Executor Memory");
  if (execMemBar && config.spark_executor_memory) {
    const allocGb = parseMemoryGb(config.spark_executor_memory);
    const maxGb = parseMemoryGb(execMemBar.max_capacity);
    result.push({
      ...execMemBar,
      allocated: config.spark_executor_memory,
      allocated_pct: maxGb ? Math.round((allocGb / maxGb) * 1000) / 10 : 0,
    });
  } else if (execMemBar) {
    result.push(execMemBar);
  }

  const cpuBar = barMap.get("CPU Cores");
  if (cpuBar && config.spark_executor_cores != null) {
    const max = parseFloat(cpuBar.max_capacity) || 0;
    result.push({
      ...cpuBar,
      allocated: String(config.spark_executor_cores),
      allocated_pct: max ? Math.round((config.spark_executor_cores / max) * 1000) / 10 : 0,
    });
  } else if (cpuBar) {
    result.push(cpuBar);
  }

  const execBar = barMap.get("Executors");
  if (execBar && config.spark_num_executors != null) {
    const max = parseFloat(execBar.max_capacity) || 0;
    result.push({
      ...execBar,
      allocated: String(config.spark_num_executors),
      allocated_pct: max ? Math.round((config.spark_num_executors / max) * 1000) / 10 : 0,
    });
  } else if (execBar) {
    result.push(execBar);
  }

  return result;
}

function computeRunStats(runs: DurationRun[]) {
  if (runs.length === 0) return { avg: null, min: null, max: null, count: 0, successRate: null };
  const durations = runs.map((r) => r.duration_seconds);
  const avg = durations.reduce((a, b) => a + b, 0) / durations.length;
  const min = Math.min(...durations);
  const max = Math.max(...durations);
  const successCount = runs.filter((r) => r.status === "success").length;
  const successRate = Math.round((successCount / runs.length) * 1000) / 10;
  return { avg, min, max, count: runs.length, successRate };
}

// --- Main Card ---
export function ResourcePerformanceCard({ pipelineId }: ResourcePerformanceCardProps) {
  const { data, isLoading } = useResourceMetrics(pipelineId);
  const selectedDagId = usePipelineStore((s) => s.selectedDagId);

  return (
    <div className="col-span-12 bg-[#18181b] border border-white/5 rounded-2xl p-5 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Gauge className="w-3.5 h-3.5 text-slate-500" />
          <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500">
            Resource & Performance
          </h3>
        </div>
        <DateRangePicker />
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
                  <MetricsSourceBadge source={data.actual_usage.metrics_source} />
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
    </div>
  );
}
