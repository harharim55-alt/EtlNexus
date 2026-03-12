export interface StatusStyle {
  /** Tailwind class for filled dot background */
  dot: string;
  /** Tailwind class for glow shadow */
  glow: string;
  /** Human-readable label */
  label: string;
  /** Tailwind text color class */
  text: string;
  /** Tailwind background class for pills/badges */
  bg: string;
  /** Tailwind classes for active filter pill state */
  activePill: string;
}

export const STATUS_CONFIG: Record<string, StatusStyle> = {
  // --- Existing statuses (colors preserved) ---
  success: {
    dot: "bg-emerald-400",
    glow: "shadow-[0_0_8px_rgba(52,211,153,0.7)]",
    label: "Success",
    text: "text-emerald-400/80",
    bg: "bg-emerald-500/8",
    activePill: "text-emerald-300 bg-emerald-500/15 border-emerald-500/30",
  },
  failed: {
    dot: "bg-rose-400",
    glow: "shadow-[0_0_8px_rgba(251,113,133,0.7)]",
    label: "Failed",
    text: "text-rose-400/80",
    bg: "bg-rose-500/8",
    activePill: "text-rose-300 bg-rose-500/15 border-rose-500/30",
  },
  upstream_failed: {
    dot: "bg-orange-400",
    glow: "shadow-[0_0_8px_rgba(251,146,60,0.7)]",
    label: "Upstream Failed",
    text: "text-orange-400/80",
    bg: "bg-orange-500/8",
    activePill: "text-orange-300 bg-orange-500/15 border-orange-500/30",
  },
  running: {
    dot: "bg-amber-400 animate-pulse",
    glow: "shadow-[0_0_8px_rgba(251,191,36,0.7)]",
    label: "Running",
    text: "text-amber-400/80",
    bg: "bg-amber-500/8",
    activePill: "text-amber-300 bg-amber-500/15 border-amber-500/30",
  },
  queued: {
    dot: "bg-sky-400",
    glow: "shadow-[0_0_8px_rgba(56,189,248,0.5)]",
    label: "Queued",
    text: "text-sky-400/80",
    bg: "bg-sky-500/8",
    activePill: "text-sky-300 bg-sky-500/15 border-sky-500/30",
  },
  // --- New Airflow statuses ---
  skipped: {
    dot: "bg-pink-400",
    glow: "shadow-[0_0_8px_rgba(244,114,182,0.5)]",
    label: "Skipped",
    text: "text-pink-400/80",
    bg: "bg-pink-500/8",
    activePill: "text-pink-300 bg-pink-500/15 border-pink-500/30",
  },
  up_for_retry: {
    dot: "bg-yellow-400",
    glow: "shadow-[0_0_8px_rgba(250,204,21,0.5)]",
    label: "Up For Retry",
    text: "text-yellow-400/80",
    bg: "bg-yellow-500/8",
    activePill: "text-yellow-300 bg-yellow-500/15 border-yellow-500/30",
  },
  deferred: {
    dot: "bg-purple-400",
    glow: "shadow-[0_0_8px_rgba(192,132,252,0.5)]",
    label: "Deferred",
    text: "text-purple-400/80",
    bg: "bg-purple-500/8",
    activePill: "text-purple-300 bg-purple-500/15 border-purple-500/30",
  },
  scheduled: {
    dot: "bg-cyan-400",
    glow: "shadow-[0_0_8px_rgba(34,211,238,0.5)]",
    label: "Scheduled",
    text: "text-cyan-400/80",
    bg: "bg-cyan-500/8",
    activePill: "text-cyan-300 bg-cyan-500/15 border-cyan-500/30",
  },
  up_for_reschedule: {
    dot: "bg-teal-400",
    glow: "shadow-[0_0_8px_rgba(45,212,191,0.5)]",
    label: "Up For Reschedule",
    text: "text-teal-400/80",
    bg: "bg-teal-500/8",
    activePill: "text-teal-300 bg-teal-500/15 border-teal-500/30",
  },
  removed: {
    dot: "bg-zinc-400",
    glow: "",
    label: "Removed",
    text: "text-zinc-400/80",
    bg: "bg-zinc-500/8",
    activePill: "text-zinc-300 bg-zinc-500/15 border-zinc-500/30",
  },
  restarting: {
    dot: "bg-violet-400 animate-pulse",
    glow: "shadow-[0_0_8px_rgba(167,139,250,0.5)]",
    label: "Restarting",
    text: "text-violet-400/80",
    bg: "bg-violet-500/8",
    activePill: "text-violet-300 bg-violet-500/15 border-violet-500/30",
  },
  no_status: {
    dot: "bg-slate-400",
    glow: "",
    label: "No Status",
    text: "text-slate-400/80",
    bg: "bg-slate-500/8",
    activePill: "text-slate-300 bg-slate-500/15 border-slate-500/30",
  },
  // --- Fallback ---
  unknown: {
    dot: "bg-slate-500",
    glow: "",
    label: "Unknown",
    text: "text-slate-500",
    bg: "bg-white/[0.02]",
    activePill: "text-slate-300 bg-slate-500/15 border-slate-500/30",
  },
};

/** Get status style config, falling back to "unknown" for unrecognized statuses */
export function getStatusStyle(status: string): StatusStyle {
  return STATUS_CONFIG[status] ?? STATUS_CONFIG.unknown;
}

/** Priority order for determining the "worst" status for glow indicators (first = highest severity) */
export const STATUS_SEVERITY_ORDER: readonly string[] = [
  "failed", "upstream_failed", "restarting", "up_for_retry",
  "running", "up_for_reschedule", "queued", "scheduled", "deferred",
  "skipped", "success", "removed", "no_status", "unknown",
];
