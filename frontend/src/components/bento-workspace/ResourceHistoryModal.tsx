import { useEffect, useState, useCallback } from "react";
import { X, Activity, GitCompareArrows } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useResourceHistory } from "@/hooks/use-resource-history";
import { formatDuration, formatDateShort, formatDateFull } from "@/lib/format";
import { formatBytes } from "./resource-performance/resource-utils";
import { ResourceChart } from "./ResourceChart";
import type { ResourceHistoryRecord } from "@/types/resources";

/* ── Props ─────────────────────────────────────────────────────────── */

interface ResourceHistoryModalProps {
  open: boolean;
  onClose: () => void;
  pipelineId: string;
}

/* ── Percentile utility ────────────────────────────────────────────── */

function percentile(arr: number[], p: number): number {
  const sorted = [...arr].sort((a, b) => a - b);
  const idx = Math.ceil((p / 100) * sorted.length) - 1;
  return sorted[Math.max(0, idx)];
}

/* ── Helpers ───────────────────────────────────────────────────────── */

function prepareData(records: ResourceHistoryRecord[]) {
  return records.map((r) => ({
    ...r,
    date: formatDateShort(r.execution_date),
    dateFull: formatDateFull(r.execution_date),
    durationDisplay: r.duration_seconds != null ? formatDuration(r.duration_seconds) : null,
    driverMemGb: r.driver_memory_used_mb != null ? +(r.driver_memory_used_mb / 1024).toFixed(2) : null,
    executorMemGb: r.executor_memory_peak_mb != null ? +(r.executor_memory_peak_mb / 1024).toFixed(2) : null,
    peakExecMemGb: r.peak_execution_memory != null ? +(r.peak_execution_memory / (1024 * 1024 * 1024)).toFixed(2) : null,
  }));
}

type ChartDatum = ReturnType<typeof prepareData>[number];

function statusDotColor(status: string): string {
  if (status === "success") return "#10b981";
  if (status === "failed") return "#f43f5e";
  if (status === "running") return "#f59e0b";
  return "#64748b";
}

/* ── Custom dot for duration chart ─────────────────────────────────── */

function StatusDot(props: {
  cx?: number;
  cy?: number;
  payload?: ChartDatum;
  p90?: number;
}) {
  const { cx, cy, payload, p90 } = props;
  if (cx == null || cy == null || !payload) return null;
  const isAnomaly =
    p90 != null &&
    payload.duration_seconds != null &&
    payload.duration_seconds > p90;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={isAnomaly ? 4 : 3}
      fill={isAnomaly ? "#f43f5e" : statusDotColor(payload.status)}
      stroke={isAnomaly ? "#f43f5e" : "none"}
      strokeWidth={isAnomaly ? 1.5 : 0}
      fillOpacity={isAnomaly ? 1 : 0.9}
    />
  );
}

/* ── Generic anomaly dot for any metric ───────────────────────────── */

function AnomalyDot(props: {
  cx?: number;
  cy?: number;
  value?: number;
  p90: number;
  normalColor: string;
}) {
  const { cx, cy, value, p90, normalColor } = props;
  if (cx == null || cy == null || value == null) return null;
  const isAnomaly = value > p90;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={isAnomaly ? 4 : 2}
      fill={isAnomaly ? "#f43f5e" : normalColor}
      stroke={isAnomaly ? "#f43f5e" : "none"}
      strokeWidth={isAnomaly ? 1.5 : 0}
    />
  );
}

/* ── Tooltip formatters ────────────────────────────────────────────── */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function durationTooltipFormatter(value: any, _name: any, props: any) {
  const payload = props?.payload as ChartDatum | undefined;
  const base = formatDuration(Number(value));
  if (payload?.failure_reason) {
    return [`${base} \u2014 FAILED: ${payload.failure_reason}`, "Duration"] as [string, string];
  }
  return [base, "Duration"] as [string, string];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function gbTooltipFormatter(value: any, name: any) {
  return [`${Number(value).toFixed(2)} GB`, name] as [string, string];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function pctTooltipFormatter(value: any) {
  return [`${Number(value).toFixed(1)}%`, "CPU"] as [string, string];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function bytesTooltipFormatter(value: any, name: any) {
  return [formatBytes(Number(value)), name] as [string, string];
}

function bytesTickFormatter(value: number) {
  return formatBytes(value);
}

function gbTickFormatter(value: number) {
  return `${value}g`;
}

/* ── Modal ─────────────────────────────────────────────────────────── */

/* ── Run Comparison Panel ──────────────────────────────────────────── */

function RunComparisonPanel({
  runs,
  onClear,
}: {
  runs: ChartDatum[];
  onClear: () => void;
}) {
  if (runs.length < 2) return null;
  const [a, b] = runs;

  const metrics: { label: string; key: keyof ChartDatum; format: (v: number | null | undefined) => string }[] = [
    { label: "Duration", key: "duration_seconds", format: (v) => v != null ? formatDuration(v as number) : "\u2014" },
    { label: "Driver Mem", key: "driverMemGb", format: (v) => v != null ? `${(v as number).toFixed(2)} GB` : "\u2014" },
    { label: "Executor Mem", key: "executorMemGb", format: (v) => v != null ? `${(v as number).toFixed(2)} GB` : "\u2014" },
    { label: "CPU %", key: "cpu_utilization_pct", format: (v) => v != null ? `${(v as number).toFixed(1)}%` : "\u2014" },
    { label: "Input", key: "input_bytes", format: (v) => v != null ? formatBytes(v as number) : "\u2014" },
    { label: "Shuffle Read", key: "shuffle_read_bytes", format: (v) => v != null ? formatBytes(v as number) : "\u2014" },
  ];

  function delta(aVal: number | null | undefined, bVal: number | null | undefined): string {
    if (aVal == null || bVal == null) return "\u2014";
    const diff = (bVal as number) - (aVal as number);
    const pct = (aVal as number) !== 0 ? ((diff / (aVal as number)) * 100).toFixed(1) : "\u2014";
    const sign = diff > 0 ? "+" : "";
    return `${sign}${pct}%`;
  }

  function deltaColor(aVal: number | null | undefined, bVal: number | null | undefined): string {
    if (aVal == null || bVal == null) return "text-zinc-500";
    const diff = (bVal as number) - (aVal as number);
    if (diff > 0) return "text-red-400";
    if (diff < 0) return "text-emerald-400";
    return "text-zinc-500";
  }

  return (
    <div className="mt-4 bg-hover-bg border border-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[9px] font-mono uppercase tracking-widest text-text-faint">Run Comparison</span>
        <button onClick={onClear} className="text-[9px] font-mono text-text-muted hover:text-foreground px-2 py-0.5 rounded border border-border hover:border-indigo-500/30 transition-all">
          Clear
        </button>
      </div>
      <div className="grid grid-cols-[1fr_1fr_1fr_80px] gap-2 text-[10px] font-mono">
        <div className="text-text-faint">Metric</div>
        <div className="text-text-faint">{a.date} ({a.status})</div>
        <div className="text-text-faint">{b.date} ({b.status})</div>
        <div className="text-text-faint">Delta</div>
        {metrics.map((m) => {
          const aVal = a[m.key] as number | null | undefined;
          const bVal = b[m.key] as number | null | undefined;
          return (
            <div key={m.label} className="contents">
              <div className="text-text-secondary">{m.label}</div>
              <div className="text-foreground">{m.format(aVal)}</div>
              <div className="text-foreground">{m.format(bVal)}</div>
              <div className={deltaColor(aVal, bVal)}>{delta(aVal, bVal)}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function ResourceHistoryModal({
  open,
  onClose,
  pipelineId,
}: ResourceHistoryModalProps) {
  const { data, isLoading } = useResourceHistory(open ? pipelineId : null);
  const [compareMode, setCompareMode] = useState(false);
  const [selectedRuns, setSelectedRuns] = useState<string[]>([]);

  const handleChartClick = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (chartData: any) => {
      if (!compareMode || !chartData?.activePayload?.[0]?.payload) return;
      const runId = chartData.activePayload[0].payload.dag_run_id as string;
      if (!runId) return;
      setSelectedRuns((prev) => {
        if (prev.includes(runId)) return prev.filter((id) => id !== runId);
        if (prev.length >= 2) return [prev[1], runId];
        return [...prev, runId];
      });
    },
    [compareMode],
  );

  // Reset compare state when closing
  useEffect(() => {
    if (!open) {
      setCompareMode(false);
      setSelectedRuns([]);
    }
  }, [open]);

  // Escape key
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  const chartData = data ? prepareData(data.records) : [];

  const hasSpill = chartData.some(
    (d) => (d.memory_bytes_spilled ?? 0) > 0 || (d.disk_bytes_spilled ?? 0) > 0,
  );
  const hasShuffle = chartData.some(
    (d) => (d.shuffle_read_bytes ?? 0) > 0 || (d.shuffle_write_bytes ?? 0) > 0,
  );
  const hasIO = chartData.some(
    (d) => (d.input_bytes ?? 0) > 0 || (d.output_bytes ?? 0) > 0,
  );
  const hasPeakExec = chartData.some((d) => d.peakExecMemGb != null);

  // Compute p90 thresholds for anomaly detection
  const durationValues = chartData
    .map((d) => d.duration_seconds)
    .filter((v): v is number => v != null);
  const p90Duration = durationValues.length >= 3 ? percentile(durationValues, 90) : null;

  const cpuValues = chartData
    .map((d) => d.cpu_utilization_pct)
    .filter((v): v is number => v != null);
  const p90Cpu = cpuValues.length >= 3 ? percentile(cpuValues, 90) : null;

  const driverMemValues = chartData
    .map((d) => d.driverMemGb)
    .filter((v): v is number => v != null);
  const p90DriverMem = driverMemValues.length >= 3 ? percentile(driverMemValues, 90) : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/85 backdrop-blur-md animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal panel */}
      <div className="relative w-full max-w-[92vw] h-[88vh] bg-surface-modal border border-border rounded-2xl shadow-2xl shadow-black/60 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-3.5 border-b border-border bg-surface-modal-header flex items-center gap-4 shrink-0">
          <div className="size-8 bg-indigo-500/10 border border-indigo-500/20 rounded-lg flex items-center justify-center shrink-0">
            <Activity className="size-4 text-indigo-400" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-foreground tracking-tight truncate">
              Resource Usage Over Time
            </h2>
            <p className="text-[10px] text-text-faint font-mono mt-0.5">
              Per-run resource metrics history
            </p>
          </div>

          <div className="w-px h-5 bg-hover-bg-strong mx-1" />
          <div className="flex items-center gap-2 text-[10px] font-mono text-text-muted">
            <span className="px-2 py-1 rounded bg-hover-bg border border-border">
              {data?.total ?? 0} runs
            </span>
            <button
              type="button"
              onClick={() => {
                setCompareMode((prev) => !prev);
                setSelectedRuns([]);
              }}
              className={`px-2 py-1 rounded border transition-all flex items-center gap-1.5 ${
                compareMode
                  ? "bg-indigo-500/20 border-indigo-500/30 text-indigo-400"
                  : "bg-hover-bg border-border text-text-muted hover:border-indigo-500/30 hover:text-indigo-400"
              }`}
            >
              <GitCompareArrows className="w-3 h-3" />
              Compare
            </button>
          </div>

          <div className="flex-1" />

          <button
            onClick={onClose}
            className="p-1.5 text-text-faint hover:text-foreground hover:bg-hover-bg rounded-lg transition-all border border-transparent hover:border-border"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto custom-scrollbar p-6">
          {isLoading ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-[260px] bg-hover-bg rounded-xl" />
              ))}
            </div>
          ) : chartData.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <span className="text-xs text-text-faint font-mono">
                No resource history available
              </span>
            </div>
          ) : (
            <>
              {compareMode && (
                <div className="mb-4 px-3 py-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-[10px] font-mono text-indigo-300">
                  Click two data points on the Duration chart to compare runs
                  {selectedRuns.length === 1 && " \u2014 1 selected, pick another"}
                </div>
              )}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Duration */}
                <div className={compareMode ? "cursor-crosshair" : undefined}>
                  <ResourceChart
                    title="Run Duration"
                    data={chartData}
                    chartType="line"
                    yTickFormatter={(v: number) => formatDuration(v)}
                    tooltipFormatter={durationTooltipFormatter}
                    referenceLines={
                      p90Duration != null
                        ? [{ y: p90Duration, stroke: "#f59e0b", label: `p90 ${formatDuration(p90Duration)}` }]
                        : undefined
                    }
                    lines={[
                      { dataKey: "duration_seconds", stroke: "#818cf8", name: "Duration", dot: <StatusDot p90={p90Duration ?? undefined} /> },
                    ]}
                    onChartClick={compareMode ? handleChartClick : undefined}
                  />
                </div>

                {/* Memory */}
                <ResourceChart
                  title="Memory Usage"
                  data={chartData}
                  chartType="line"
                  yTickFormatter={gbTickFormatter}
                  tooltipFormatter={gbTooltipFormatter}
                  showLegend
                  referenceLines={
                    p90DriverMem != null
                      ? [{ y: p90DriverMem, stroke: "#f59e0b", label: `p90 ${p90DriverMem.toFixed(1)}g` }]
                      : undefined
                  }
                  lines={[
                    {
                      dataKey: "driverMemGb",
                      stroke: "#818cf8",
                      name: "Driver",
                      dot: p90DriverMem != null
                        ? <AnomalyDot p90={p90DriverMem} normalColor="#818cf8" />
                        : { r: 2, fill: "#818cf8" },
                    },
                    { dataKey: "executorMemGb", stroke: "#34d399", name: "Executor Peak" },
                    ...(hasPeakExec
                      ? [{ dataKey: "peakExecMemGb", stroke: "#f59e0b", name: "Peak Exec", strokeDasharray: "4 2" }]
                      : []),
                  ]}
                />

                {/* CPU Utilization */}
                <ResourceChart
                  title="CPU Utilization"
                  data={chartData}
                  chartType="area"
                  yTickFormatter={(v: number) => `${v}%`}
                  yDomain={[0, 100]}
                  tooltipFormatter={pctTooltipFormatter}
                  referenceLines={
                    p90Cpu != null
                      ? [{ y: p90Cpu, stroke: "#f59e0b", label: `p90 ${p90Cpu.toFixed(0)}%` }]
                      : undefined
                  }
                  gradientDefs={
                    <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#818cf8" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#818cf8" stopOpacity={0.02} />
                    </linearGradient>
                  }
                  areas={[
                    {
                      dataKey: "cpu_utilization_pct",
                      stroke: "#818cf8",
                      fill: "url(#cpuGradient)",
                      name: "CPU",
                      dot: p90Cpu != null
                        ? <AnomalyDot p90={p90Cpu} normalColor="#818cf8" />
                        : { r: 2, fill: "#818cf8" },
                    },
                  ]}
                />

                {/* Shuffle I/O */}
                {hasShuffle && (
                  <ResourceChart
                    title="Shuffle I/O"
                    data={chartData}
                    chartType="line"
                    yTickFormatter={bytesTickFormatter}
                    tooltipFormatter={bytesTooltipFormatter}
                    showLegend
                    lines={[
                      { dataKey: "shuffle_read_bytes", stroke: "#818cf8", name: "Shuffle Read" },
                      { dataKey: "shuffle_write_bytes", stroke: "#f472b6", name: "Shuffle Write" },
                    ]}
                  />
                )}

                {/* Data I/O */}
                {hasIO && (
                  <ResourceChart
                    title="Data I/O"
                    data={chartData}
                    chartType="line"
                    yTickFormatter={bytesTickFormatter}
                    tooltipFormatter={bytesTooltipFormatter}
                    showLegend
                    lines={[
                      { dataKey: "input_bytes", stroke: "#34d399", name: "Input" },
                      { dataKey: "output_bytes", stroke: "#fb923c", name: "Output" },
                    ]}
                  />
                )}

                {/* Spill */}
                {hasSpill && (
                  <ResourceChart
                    title="Memory & Disk Spill"
                    data={chartData}
                    chartType="bar"
                    yTickFormatter={bytesTickFormatter}
                    tooltipFormatter={bytesTooltipFormatter}
                    showLegend
                    bars={[
                      { dataKey: "memory_bytes_spilled", fill: "#f59e0b", fillOpacity: 0.7, name: "Mem Spill" },
                      { dataKey: "disk_bytes_spilled", fill: "#ef4444", fillOpacity: 0.7, name: "Disk Spill" },
                    ]}
                  />
                )}
              </div>

              {/* Run Comparison Panel */}
              {compareMode && selectedRuns.length === 2 && (
                <RunComparisonPanel
                  runs={selectedRuns.map((id) => chartData.find((d) => d.dag_run_id === id)!).filter(Boolean)}
                  onClear={() => setSelectedRuns([])}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
