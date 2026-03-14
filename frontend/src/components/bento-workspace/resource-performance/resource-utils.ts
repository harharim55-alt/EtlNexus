import type { CapacityBar as CapacityBarType, DurationRun, ResourceConfigEntry } from "@/types/resources";
import { HardDrive, MemoryStick, Cpu, Server } from "lucide-react";

export const RESOURCE_ICONS = {
  driver: HardDrive,
  executor: MemoryStick,
  cores: Cpu,
  executors: Server,
} as const;

export function statusColor(status: string): string {
  switch (status) {
    case "success": return "bg-emerald-500";
    case "failed": return "bg-rose-500";
    case "running": return "bg-amber-500";
    default: return "bg-slate-600";
  }
}

export function capacityColor(pct: number): string {
  if (pct >= 80) return "bg-rose-500";
  if (pct >= 60) return "bg-amber-500";
  return "bg-emerald-500";
}

export function capacityTextColor(pct: number): string {
  if (pct >= 80) return "text-rose-400";
  if (pct >= 60) return "text-amber-400";
  return "text-emerald-400";
}

export function formatBytes(bytes: number | null): string {
  if (bytes == null || bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(1024));
  const idx = Math.min(i, units.length - 1);
  return `${(bytes / Math.pow(1024, idx)).toFixed(idx > 1 ? 1 : 0)} ${units[idx]}`;
}

export function formatMs(ms: number | null): string {
  if (ms == null) return "\u2014";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60_000).toFixed(1)}m`;
}

export function parseMemoryGb(mem: string): number {
  const match = mem.trim().match(/^(\d+(?:\.\d+)?)\s*([gmtGMT]?)$/);
  if (!match) return 0;
  const val = parseFloat(match[1]);
  const unit = match[2].toLowerCase();
  if (unit === "m") return val / 1024;
  if (unit === "t") return val * 1024;
  return val;
}

export function recomputeCapacityBars(
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

export function computeRunStats(runs: DurationRun[]) {
  if (runs.length === 0) return { avg: null, min: null, max: null, count: 0, successRate: null };
  const durations = runs.map((r) => r.duration_seconds);
  const avg = durations.reduce((a, b) => a + b, 0) / durations.length;
  const min = Math.min(...durations);
  const max = Math.max(...durations);
  const successCount = runs.filter((r) => r.status === "success").length;
  const successRate = Math.round((successCount / runs.length) * 1000) / 10;
  return { avg, min, max, count: runs.length, successRate };
}
