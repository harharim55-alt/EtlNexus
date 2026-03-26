import { useEffect } from "react";
import { X, Activity } from "lucide-react";
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
}) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || !payload) return null;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={3}
      fill={statusDotColor(payload.status)}
      stroke="none"
    />
  );
}

/* ── Tooltip formatters ────────────────────────────────────────────── */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function durationTooltipFormatter(value: any) {
  return [formatDuration(Number(value)), "Duration"] as [string, string];
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

export function ResourceHistoryModal({
  open,
  onClose,
  pipelineId,
}: ResourceHistoryModalProps) {
  const { data, isLoading } = useResourceHistory(open ? pipelineId : null);

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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/85 backdrop-blur-md animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal panel */}
      <div className="relative w-full max-w-[92vw] h-[88vh] bg-[#0a0a0f] border border-white/[0.06] rounded-2xl shadow-2xl shadow-black/60 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-3.5 border-b border-white/[0.06] bg-[#0e0e14] flex items-center gap-4 shrink-0">
          <div className="size-8 bg-indigo-500/10 border border-indigo-500/20 rounded-lg flex items-center justify-center shrink-0">
            <Activity className="size-4 text-indigo-400" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-white tracking-tight truncate">
              Resource Usage Over Time
            </h2>
            <p className="text-[10px] text-slate-600 font-mono mt-0.5">
              Per-run resource metrics history
            </p>
          </div>

          <div className="w-px h-5 bg-white/[0.06] mx-1" />
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500">
            <span className="px-2 py-1 rounded bg-white/[0.03] border border-white/[0.05]">
              {data?.total ?? 0} runs
            </span>
          </div>

          <div className="flex-1" />

          <button
            onClick={onClose}
            className="p-1.5 text-slate-600 hover:text-white hover:bg-white/5 rounded-lg transition-all border border-transparent hover:border-white/[0.06]"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto custom-scrollbar p-6">
          {isLoading ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-[260px] bg-white/5 rounded-xl" />
              ))}
            </div>
          ) : chartData.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <span className="text-xs text-slate-600 font-mono">
                No resource history available
              </span>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Duration */}
              <ResourceChart
                title="Run Duration"
                data={chartData}
                chartType="line"
                yTickFormatter={(v: number) => formatDuration(v)}
                tooltipFormatter={durationTooltipFormatter}
                lines={[
                  { dataKey: "duration_seconds", stroke: "#818cf8", name: "Duration", dot: <StatusDot /> },
                ]}
              />

              {/* Memory */}
              <ResourceChart
                title="Memory Usage"
                data={chartData}
                chartType="line"
                yTickFormatter={gbTickFormatter}
                tooltipFormatter={gbTooltipFormatter}
                showLegend
                lines={[
                  { dataKey: "driverMemGb", stroke: "#818cf8", name: "Driver" },
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
                gradientDefs={
                  <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#818cf8" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#818cf8" stopOpacity={0.02} />
                  </linearGradient>
                }
                areas={[
                  { dataKey: "cpu_utilization_pct", stroke: "#818cf8", fill: "url(#cpuGradient)", name: "CPU" },
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
          )}
        </div>
      </div>
    </div>
  );
}
