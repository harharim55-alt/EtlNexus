import type { LucideIcon } from "lucide-react";

/* ── Props ─────────────────────────────────────────────────────────── */

interface ResourceMetricCardProps {
  icon: LucideIcon;
  label: string;
  value: string;
  /** Additional detail line (e.g., actual usage) */
  detail?: string | null;
  /** Icon color class (defaults to text-text-faint) */
  iconColor?: string;
  /** Whether this metric should show a warning style */
  warn?: boolean;
}

/* ── Component ─────────────────────────────────────────────────────── */

export function ResourceMetricCard({
  icon: Icon,
  label,
  value,
  detail,
  iconColor = "text-text-faint",
  warn = false,
}: ResourceMetricCardProps) {
  return (
    <div className="flex items-start gap-2">
      <Icon className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${warn ? "text-amber-500" : iconColor}`} />
      <div className="min-w-0">
        <div className="text-[9px] font-mono uppercase tracking-widest text-text-faint">
          {label}
        </div>
        <div className={`text-sm font-medium font-mono ${warn ? "text-amber-400" : "text-foreground"}`}>
          {value}
        </div>
        {detail && (
          <div className="text-[10px] font-mono text-indigo-400">
            {detail}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Compact variant for Spark Internals ─────────────────────────── */

interface CompactMetricCardProps {
  icon: LucideIcon;
  label: string;
  value: string;
  warn?: boolean;
}

export function CompactMetricCard({
  icon: Icon,
  label,
  value,
  warn = false,
}: CompactMetricCardProps) {
  return (
    <div className="flex items-start gap-1.5">
      <Icon className={`w-3 h-3 mt-0.5 shrink-0 ${warn ? "text-amber-500" : "text-text-faint"}`} />
      <div className="min-w-0">
        <div className="text-[8px] font-mono uppercase tracking-widest text-text-faint truncate">
          {label}
        </div>
        <div className={`text-xs font-mono ${warn ? "text-amber-400" : "text-foreground"}`}>
          {value}
        </div>
      </div>
    </div>
  );
}
