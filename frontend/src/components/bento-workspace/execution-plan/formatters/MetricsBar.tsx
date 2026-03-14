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
    <div className="flex flex-wrap items-center gap-3 px-4 py-2.5 bg-black/20 rounded-xl border border-white/[0.04]">
      {timeEntry && (
        <span className="text-[11px] font-mono text-slate-300 flex items-center gap-1.5">
          <span className="text-slate-500">⏱</span>
          {timeEntry[1]}
        </span>
      )}
      {rows && (
        <span className="text-[11px] font-mono text-slate-300 flex items-center gap-1.5">
          <span className="text-slate-500">≣</span>
          {rows} rows
        </span>
      )}
      {rest.map(([key, val]) => (
        <span
          key={key}
          className="text-[11px] font-mono text-slate-400"
        >
          <span className="text-slate-600">{key}</span>{" "}
          {val}
        </span>
      ))}
    </div>
  );
}
