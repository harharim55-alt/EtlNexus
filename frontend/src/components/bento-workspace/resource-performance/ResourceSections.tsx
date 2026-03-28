import { CheckCircle, Activity, ArrowDownUp, Database, HardDrive, MemoryStick, TrendingUp, TrendingDown, Minus, AlertTriangle, Lightbulb } from "lucide-react";
import { formatDuration, formatDateFull } from "@/lib/format";
import type { ActualUsage, CapacityBar as CapacityBarType, DurationRun, ResourceConfigEntry, TrendAnalysis, ResourceRecommendation } from "@/types/resources";
import {
  RESOURCE_ICONS,
  statusColor,
  capacityColor,
  capacityTextColor,
  formatBytes,
  formatMs,
} from "./resource-utils";
import { ResourceMetricCard, CompactMetricCard } from "./ResourceMetricCard";

// --- Trend Indicator (inline) ---
function TrendIndicator({ trend }: { trend: TrendAnalysis }) {
  if (trend.confidence < 0.3) return null;
  const icon = trend.direction === "increasing"
    ? <TrendingUp className="h-3 w-3 text-red-400" />
    : trend.direction === "decreasing"
    ? <TrendingDown className="h-3 w-3 text-emerald-400" />
    : <Minus className="h-3 w-3 text-zinc-500" />;
  return (
    <span className="inline-flex items-center gap-1 text-[10px]" title={trend.message}>
      {icon}
    </span>
  );
}

// --- Duration Section ---
interface DurationSectionProps {
  avgDuration: number | null;
  minDuration: number | null;
  maxDuration: number | null;
  runCount: number;
  successRate: number | null;
  recentRuns: DurationRun[];
  p50Duration?: number | null;
  p95Duration?: number | null;
  p99Duration?: number | null;
  trends?: TrendAnalysis[];
}

export function DurationSection({
  avgDuration,
  minDuration,
  maxDuration,
  runCount,
  successRate,
  recentRuns,
  p50Duration,
  p95Duration,
  p99Duration,
  trends,
}: DurationSectionProps) {
  if (runCount === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-xs text-text-faint font-mono">No run history</span>
      </div>
    );
  }

  const maxBarDuration = Math.max(...recentRuns.map((r) => r.duration_seconds), 1);
  const durationTrend = trends?.find((t) => t.metric === "duration");

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-end gap-2">
        <span className="text-2xl font-semibold text-foreground font-mono tracking-tight">
          {avgDuration != null ? formatDuration(avgDuration) : "\u2014"}
        </span>
        <span className="text-[10px] text-text-muted font-mono uppercase mb-1">avg</span>
        {durationTrend && <TrendIndicator trend={durationTrend} />}
      </div>
      <div className="flex items-center gap-3 text-[10px] font-mono text-text-muted">
        <span>
          min {minDuration != null ? formatDuration(minDuration) : "\u2014"}
        </span>
        <span className="text-border-prominent">|</span>
        <span>
          max {maxDuration != null ? formatDuration(maxDuration) : "\u2014"}
        </span>
        <span className="text-border-prominent">|</span>
        <span>{runCount} runs</span>
      </div>
      {(p50Duration != null || p95Duration != null || p99Duration != null) && (
        <div className="flex items-center gap-3 text-[10px] font-mono text-zinc-500">
          {p50Duration != null && <span>p50: {formatDuration(p50Duration)}</span>}
          {p95Duration != null && <span>p95: {formatDuration(p95Duration)}</span>}
          {p99Duration != null && <span>p99: {formatDuration(p99Duration)}</span>}
        </div>
      )}
      {successRate != null && (
        <div className="flex items-center gap-1.5">
          <CheckCircle className="w-3 h-3 text-emerald-500" />
          <span className="text-[10px] font-mono text-text-secondary">
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
        <span className="text-xs text-text-faint font-mono">No Spark resources</span>
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
        <span className="text-xs text-text-faint font-mono">No capacity data</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {bars.map((bar) => (
        <div key={bar.label} className="flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono uppercase tracking-widest text-text-faint">
              {bar.label}
            </span>
            <span className={`text-[10px] font-mono ${capacityTextColor(bar.allocated_pct)}`}>
              {Math.round(bar.allocated_pct)}%
            </span>
          </div>
          {/* Stacked bar: used (solid) + allocated (lighter) within capacity track */}
          <div className="relative h-2 bg-hover-bg rounded-full overflow-hidden">
            {/* Allocated fill (lighter) */}
            <div
              className="absolute inset-y-0 left-0 bg-hover-bg-strong rounded-full transition-all duration-500"
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
          <div className="text-[9px] font-mono text-text-muted">
            {bar.used !== "\u2014" ? (
              <>
                <span className="text-text-secondary">{bar.used}</span>
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
    <div className="mt-4 pt-3 border-t border-border">
      <div className="flex items-center gap-1.5 mb-2.5">
        <Activity className="w-3 h-3 text-text-faint" />
        <span className="text-[9px] font-mono uppercase tracking-widest text-text-faint">
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

// --- Recommendations Section ---
export function RecommendationsSection({ recommendations }: { recommendations: ResourceRecommendation[] }) {
  if (!recommendations?.length) return null;
  return (
    <div className="space-y-2">
      {recommendations.map((rec, i) => (
        <div key={i} className={`rounded-md px-3 py-2 text-xs ${rec.severity === "warning" ? "bg-amber-500/10 border border-amber-500/20" : "bg-blue-500/10 border border-blue-500/20"}`}>
          <div className="flex items-center gap-1.5 font-medium">
            {rec.severity === "warning" ? <AlertTriangle className="h-3 w-3 text-amber-400" /> : <Lightbulb className="h-3 w-3 text-blue-400" />}
            <span>{rec.resource}: {rec.current_value} → {rec.recommended_value}</span>
          </div>
          <p className="mt-1 text-zinc-400">{rec.reason}</p>
        </div>
      ))}
    </div>
  );
}
