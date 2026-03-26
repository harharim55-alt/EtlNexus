import { CheckCircle, Activity, ArrowDownUp, Database, HardDrive, MemoryStick } from "lucide-react";
import { formatDuration, formatDateFull } from "@/lib/format";
import type { ActualUsage, CapacityBar as CapacityBarType, DurationRun, ResourceConfigEntry } from "@/types/resources";
import {
  RESOURCE_ICONS,
  statusColor,
  capacityColor,
  capacityTextColor,
  formatBytes,
  formatMs,
} from "./resource-utils";
import { ResourceMetricCard, CompactMetricCard } from "./ResourceMetricCard";

// --- Duration Section ---
export function DurationSection({
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
          {avgDuration != null ? formatDuration(avgDuration) : "\u2014"}
        </span>
        <span className="text-[10px] text-slate-500 font-mono uppercase mb-1">avg</span>
      </div>
      <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500">
        <span>
          min {minDuration != null ? formatDuration(minDuration) : "\u2014"}
        </span>
        <span className="text-white/10">|</span>
        <span>
          max {maxDuration != null ? formatDuration(maxDuration) : "\u2014"}
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
                title={`${formatDateFull(run.execution_date)} \u2014 ${formatDuration(run.duration_seconds)} \u2014 ${run.status}`}
              />
            );
          })}
      </div>
    </div>
  );
}

// --- Resource Config Section ---
export function ResourceSection({
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
        ? `~${(actualUsage.avg_executor_memory_peak_mb / 1024).toFixed(1)}g peak avg`
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

  const peakExecMem = actualUsage.avg_peak_execution_memory;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3">
        {items.map((item) => {
          if (!item.allocated) return null;
          return (
            <ResourceMetricCard
              key={item.key}
              icon={RESOURCE_ICONS[item.key]}
              label={item.label}
              value={item.allocated}
              detail={item.actual}
            />
          );
        })}
        {peakExecMem != null && (
          <ResourceMetricCard
            icon={MemoryStick}
            label="Peak Exec Memory"
            value={formatBytes(peakExecMem)}
          />
        )}
      </div>
    </div>
  );
}

// --- Capacity Section ---
export function CapacitySection({ bars }: { bars: CapacityBarType[] }) {
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
            {bar.used !== "\u2014" && bar.used_pct > 0 && (
              <div
                className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${capacityColor(bar.used_pct)}`}
                style={{ width: `${Math.min(bar.used_pct, 100)}%` }}
              />
            )}
          </div>
          <div className="text-[9px] font-mono text-slate-500">
            {bar.used !== "\u2014" ? (
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

// --- Spark Internals Section (sparkMeasure metrics) ---
export function SparkInternalsSection({ actualUsage }: { actualUsage: ActualUsage }) {
  const hasData =
    actualUsage.avg_jvm_gc_time_ms != null ||
    actualUsage.avg_shuffle_read_bytes != null ||
    actualUsage.avg_input_bytes != null;

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
  ].filter((item) => item.value !== "0 B" && item.value !== "\u2014");

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
        {items.map((item) => (
          <CompactMetricCard
            key={item.label}
            icon={item.icon}
            label={item.label}
            value={item.value}
            warn={item.warn}
          />
        ))}
      </div>
    </div>
  );
}
