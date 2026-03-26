import { memo } from "react";
import type { PipelineListItem as PipelineListItemType } from "@/types/pipeline";
import { stripDummy, formatFreshness } from "@/lib/format";

function getSuccessRateDot(rate: number | null) {
  if (rate == null) return { color: "bg-slate-500", title: "No recent runs" };
  if (rate >= 80) return { color: "bg-emerald-500", title: `${rate}% success (30d)` };
  if (rate >= 50) return { color: "bg-amber-500", title: `${rate}% success (30d)` };
  return { color: "bg-rose-500", title: `${rate}% success (30d)` };
}

interface PipelineListItemProps {
  pipeline: PipelineListItemType;
  isActive: boolean;
  onClick: () => void;
}

export const PipelineListItem = memo(function PipelineListItem({
  pipeline,
  isActive,
  onClick,
}: PipelineListItemProps) {
  const dot = getSuccessRateDot(pipeline.success_rate);

  const fresh = formatFreshness(pipeline.last_run_at);
  const staleBorder = fresh.stale && fresh.label !== "never"
    ? "border-l-2 border-l-rose-500/30"
    : "";

  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-xl cursor-pointer transition-all duration-200 border ${staleBorder} ${
        isActive
          ? "bg-[#18181b] border-indigo-500/30 shadow-[0_4px_20px_rgba(0,0,0,0.2)]"
          : "bg-transparent border-transparent hover:bg-white/5"
      }`}
    >
      <div className="flex items-start justify-between mb-1">
        <h3
          className={`font-medium text-sm truncate pr-4 ${
            isActive ? "text-indigo-400" : "text-slate-200"
          }`}
        >
          {stripDummy(pipeline.name)}
        </h3>
        <span
          className={`shrink-0 mt-1.5 h-2 w-2 rounded-full ${dot.color}`}
          title={dot.title}
        />
      </div>
      <div className="text-xs text-slate-500 font-mono mb-3">
        {pipeline.pipeline_type === "api" ? "API" : "ETL"}
      </div>
      <div className="flex gap-2 text-[10px] font-mono">
        {pipeline.schedule && (
          <span className="px-2 py-0.5 rounded bg-white/5 text-slate-400 border border-white/5">
            {pipeline.schedule}
          </span>
        )}
        {pipeline.rows_per_day && (
          <span className="px-2 py-0.5 rounded bg-white/5 text-slate-400 border border-white/5">
            {pipeline.rows_per_day}
          </span>
        )}
        <span className={`px-2 py-0.5 rounded bg-white/5 border border-white/5 ${fresh.className}`}>
          {fresh.label === "never" ? "no runs" : fresh.label}
        </span>
      </div>
    </div>
  );
});
