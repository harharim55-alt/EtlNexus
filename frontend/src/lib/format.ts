/**
 * Shared formatting utilities used across multiple components.
 */

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins < 60) return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  const hrs = Math.floor(mins / 60);
  const remainMins = mins % 60;
  return remainMins > 0 ? `${hrs}h ${remainMins}m` : `${hrs}h`;
}

export function stripDummy(name: string): string {
  return name.replace(/Dummy$/i, "");
}

/* ── Date Formatting ─────────────────────────────────────────────── */

const EM_DASH = "\u2014";

/**
 * Compact date: "Mar 26" (current year) or "Mar 26, 2025" (other years).
 * Good for chart axes and compact badges.
 */
export function formatDateShort(iso: string | null | undefined): string {
  if (!iso) return EM_DASH;
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return EM_DASH;
    const now = new Date();
    const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
    if (d.getFullYear() !== now.getFullYear()) opts.year = "numeric";
    return d.toLocaleDateString("en-US", opts);
  } catch {
    return EM_DASH;
  }
}

/**
 * Full date+time in UTC: "Mar 26, 14:30 UTC".
 * Good for run selector items, tooltips, detailed views.
 */
export function formatDateFull(iso: string | null | undefined): string {
  if (!iso) return EM_DASH;
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return EM_DASH;
    return (
      d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "UTC",
      }) + " UTC"
    );
  } catch {
    return EM_DASH;
  }
}

/**
 * Time-only in UTC: "14:30 UTC".
 * Good for finish times and schedule-related displays.
 */
export function formatTimeUTC(iso: string | null | undefined): string {
  if (!iso) return EM_DASH;
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return EM_DASH;
    return (
      d.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "UTC",
      }) + " UTC"
    );
  } catch {
    return EM_DASH;
  }
}

/**
 * Relative time: "just now", "5m ago", "3h ago", "2d ago",
 * falling back to "Mar 26, 2025" for anything older than 7 days.
 */
export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return EM_DASH;
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return EM_DASH;
    const diffMs = Date.now() - d.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHour < 24) return `${diffHour}h ago`;
    if (diffDay < 7) return `${diffDay}d ago`;
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return EM_DASH;
  }
}

/**
 * Admin/formal date: "Mar 26, 2025" (always includes year).
 * Good for grants, user lists, team panels.
 */
export function formatDateAdmin(iso: string | null | undefined): string {
  if (!iso) return EM_DASH;
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return EM_DASH;
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return EM_DASH;
  }
}

/**
 * Freshness assessment for pipeline run recency.
 * Returns a label, stale flag, and Tailwind color class.
 */
export function formatFreshness(iso: string | null | undefined): {
  label: string;
  stale: boolean;
  className: string;
} {
  if (!iso) return { label: "never", stale: true, className: "text-slate-600" };
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return { label: "never", stale: true, className: "text-slate-600" };
    const diffMs = Date.now() - d.getTime();
    const diffHour = diffMs / (1000 * 60 * 60);
    const diffDay = diffHour / 24;

    if (diffHour < 4) {
      const h = Math.floor(diffHour);
      const m = Math.floor((diffMs / (1000 * 60)) % 60);
      const label = h > 0 ? `${h}h ago` : `${Math.max(m, 1)}m ago`;
      return { label, stale: false, className: "text-emerald-400" };
    }
    if (diffHour < 24) {
      return { label: `${Math.floor(diffHour)}h ago`, stale: false, className: "text-slate-400" };
    }
    if (diffDay < 3) {
      return { label: `${Math.floor(diffDay)}d ago`, stale: false, className: "text-amber-400" };
    }
    return { label: `${Math.floor(diffDay)}d ago`, stale: true, className: "text-rose-400" };
  } catch {
    return { label: "never", stale: true, className: "text-slate-600" };
  }
}
