import { TIME_KEYS } from "../plan-constants";

export function MetricsBar({ metrics }: { metrics: Record<string, string> }) {
  const entries = Object.entries(metrics);
  if (entries.length === 0) return null;

  const timeEntry = entries.find(([k]) => TIME_KEYS.has(k));
  const rows = metrics.rows;
  const rest = entries.filter(
    ([k]) => k !== "rows" && !TIME_KEYS.has(k),
  );

  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-2.5 bg-surface-inset rounded-xl border border-border">
      {timeEntry && (
        <span className="text-[11px] font-mono text-text-primary flex items-center gap-1.5">
          <span className="text-text-muted">⏱</span>
          {timeEntry[1]}
        </span>
      )}
      {rows && (
        <span className="text-[11px] font-mono text-text-primary flex items-center gap-1.5">
          <span className="text-text-muted">≣</span>
          {rows} rows
        </span>
      )}
      {rest.map(([key, val]) => (
        <span
          key={key}
          className="text-[11px] font-mono text-text-secondary"
        >
          <span className="text-text-faint">{key}</span>{" "}
          {val}
        </span>
      ))}
    </div>
  );
}
