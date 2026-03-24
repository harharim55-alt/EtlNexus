import { useEffect } from "react";
import { X, Activity } from "lucide-react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Skeleton } from "@/components/ui/skeleton";
import { useResourceHistory } from "@/hooks/use-resource-history";
import { formatDuration } from "@/lib/format";
import { formatBytes } from "./resource-performance/resource-utils";
import type { ResourceHistoryRecord } from "@/types/resources";

/* ── Props ─────────────────────────────────────────────────────────── */

interface ResourceHistoryModalProps {
  open: boolean;
  onClose: () => void;
  pipelineId: string;
}

/* ── Chart theme ───────────────────────────────────────────────────── */

const GRID_COLOR = "#1e293b";
const TICK_STYLE = { fill: "#64748b", fontSize: 9, fontFamily: "monospace" };
const TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: "#18181b",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 8,
    fontSize: 11,
    fontFamily: "monospace",
    color: "#e2e8f0",
  },
  labelStyle: { color: "#94a3b8", fontSize: 10 },
};

/* ── Helpers ───────────────────────────────────────────────────────── */

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function formatDateFull(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function prepareData(records: ResourceHistoryRecord[]) {
  return records.map((r) => ({
    ...r,
    date: formatDate(r.execution_date),
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

/* ── Chart section wrapper ─────────────────────────────────────────── */

function ChartPanel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-4">
      <div className="text-[9px] font-mono uppercase tracking-widest text-slate-600 mb-3">
        {title}
      </div>
      <div className="h-[200px]">{children}</div>
    </div>
  );
}

/* ── Tooltip formatters ────────────────────────────────────────────── */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function durationTooltipFormatter(value: any) {
  return [formatDuration(Number(value)), "Duration"];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function gbTooltipFormatter(value: any, name: any) {
  return [`${Number(value).toFixed(2)} GB`, name];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function pctTooltipFormatter(value: any) {
  return [`${Number(value).toFixed(1)}%`, "CPU"];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function bytesTooltipFormatter(value: any, name: any) {
  return [formatBytes(Number(value)), name];
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
              <ChartPanel title="Run Duration">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
                    <XAxis dataKey="date" tick={TICK_STYLE} axisLine={false} tickLine={false} />
                    <YAxis
                      tick={TICK_STYLE}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(v: number) => formatDuration(v)}
                    />
                    <Tooltip
                      {...TOOLTIP_STYLE}
                      formatter={durationTooltipFormatter}
                      labelFormatter={(_, payload) =>
                        payload?.[0]?.payload?.dateFull ?? ""
                      }
                    />
                    <Line
                      type="monotone"
                      dataKey="duration_seconds"
                      stroke="#818cf8"
                      strokeWidth={1.5}
                      dot={<StatusDot />}
                      name="Duration"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </ChartPanel>

              {/* Memory */}
              <ChartPanel title="Memory Usage">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
                    <XAxis dataKey="date" tick={TICK_STYLE} axisLine={false} tickLine={false} />
                    <YAxis
                      tick={TICK_STYLE}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={gbTickFormatter}
                    />
                    <Tooltip
                      {...TOOLTIP_STYLE}
                      formatter={gbTooltipFormatter}
                      labelFormatter={(_, payload) =>
                        payload?.[0]?.payload?.dateFull ?? ""
                      }
                    />
                    <Legend
                      iconSize={8}
                      wrapperStyle={{ fontSize: 9, fontFamily: "monospace" }}
                    />
                    <Line
                      type="monotone"
                      dataKey="driverMemGb"
                      stroke="#818cf8"
                      strokeWidth={1.5}
                      dot={{ r: 2, fill: "#818cf8" }}
                      name="Driver"
                    />
                    <Line
                      type="monotone"
                      dataKey="executorMemGb"
                      stroke="#34d399"
                      strokeWidth={1.5}
                      dot={{ r: 2, fill: "#34d399" }}
                      name="Executor Peak"
                    />
                    {hasPeakExec && (
                      <Line
                        type="monotone"
                        dataKey="peakExecMemGb"
                        stroke="#f59e0b"
                        strokeWidth={1.5}
                        strokeDasharray="4 2"
                        dot={{ r: 2, fill: "#f59e0b" }}
                        name="Peak Exec"
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </ChartPanel>

              {/* CPU Utilization */}
              <ChartPanel title="CPU Utilization">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#818cf8" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#818cf8" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
                    <XAxis dataKey="date" tick={TICK_STYLE} axisLine={false} tickLine={false} />
                    <YAxis
                      tick={TICK_STYLE}
                      axisLine={false}
                      tickLine={false}
                      domain={[0, 100]}
                      tickFormatter={(v: number) => `${v}%`}
                    />
                    <Tooltip
                      {...TOOLTIP_STYLE}
                      formatter={pctTooltipFormatter}
                      labelFormatter={(_, payload) =>
                        payload?.[0]?.payload?.dateFull ?? ""
                      }
                    />
                    <Area
                      type="monotone"
                      dataKey="cpu_utilization_pct"
                      stroke="#818cf8"
                      strokeWidth={1.5}
                      fill="url(#cpuGradient)"
                      dot={{ r: 2, fill: "#818cf8" }}
                      name="CPU"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </ChartPanel>

              {/* Shuffle I/O */}
              {hasShuffle && (
                <ChartPanel title="Shuffle I/O">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
                      <XAxis dataKey="date" tick={TICK_STYLE} axisLine={false} tickLine={false} />
                      <YAxis
                        tick={TICK_STYLE}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={bytesTickFormatter}
                      />
                      <Tooltip
                        {...TOOLTIP_STYLE}
                        formatter={bytesTooltipFormatter}
                        labelFormatter={(_, payload) =>
                          payload?.[0]?.payload?.dateFull ?? ""
                        }
                      />
                      <Legend
                        iconSize={8}
                        wrapperStyle={{ fontSize: 9, fontFamily: "monospace" }}
                      />
                      <Line
                        type="monotone"
                        dataKey="shuffle_read_bytes"
                        stroke="#818cf8"
                        strokeWidth={1.5}
                        dot={{ r: 2, fill: "#818cf8" }}
                        name="Shuffle Read"
                      />
                      <Line
                        type="monotone"
                        dataKey="shuffle_write_bytes"
                        stroke="#f472b6"
                        strokeWidth={1.5}
                        dot={{ r: 2, fill: "#f472b6" }}
                        name="Shuffle Write"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </ChartPanel>
              )}

              {/* Data I/O */}
              {hasIO && (
                <ChartPanel title="Data I/O">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
                      <XAxis dataKey="date" tick={TICK_STYLE} axisLine={false} tickLine={false} />
                      <YAxis
                        tick={TICK_STYLE}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={bytesTickFormatter}
                      />
                      <Tooltip
                        {...TOOLTIP_STYLE}
                        formatter={bytesTooltipFormatter}
                        labelFormatter={(_, payload) =>
                          payload?.[0]?.payload?.dateFull ?? ""
                        }
                      />
                      <Legend
                        iconSize={8}
                        wrapperStyle={{ fontSize: 9, fontFamily: "monospace" }}
                      />
                      <Line
                        type="monotone"
                        dataKey="input_bytes"
                        stroke="#34d399"
                        strokeWidth={1.5}
                        dot={{ r: 2, fill: "#34d399" }}
                        name="Input"
                      />
                      <Line
                        type="monotone"
                        dataKey="output_bytes"
                        stroke="#fb923c"
                        strokeWidth={1.5}
                        dot={{ r: 2, fill: "#fb923c" }}
                        name="Output"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </ChartPanel>
              )}

              {/* Spill */}
              {hasSpill && (
                <ChartPanel title="Memory & Disk Spill">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
                      <XAxis dataKey="date" tick={TICK_STYLE} axisLine={false} tickLine={false} />
                      <YAxis
                        tick={TICK_STYLE}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={bytesTickFormatter}
                      />
                      <Tooltip
                        {...TOOLTIP_STYLE}
                        formatter={bytesTooltipFormatter}
                        labelFormatter={(_, payload) =>
                          payload?.[0]?.payload?.dateFull ?? ""
                        }
                      />
                      <Legend
                        iconSize={8}
                        wrapperStyle={{ fontSize: 9, fontFamily: "monospace" }}
                      />
                      <Bar
                        dataKey="memory_bytes_spilled"
                        fill="#f59e0b"
                        fillOpacity={0.7}
                        name="Mem Spill"
                        radius={[2, 2, 0, 0]}
                      />
                      <Bar
                        dataKey="disk_bytes_spilled"
                        fill="#ef4444"
                        fillOpacity={0.7}
                        name="Disk Spill"
                        radius={[2, 2, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartPanel>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
