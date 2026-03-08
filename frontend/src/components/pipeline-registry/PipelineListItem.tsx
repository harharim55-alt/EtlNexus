import { memo } from "react";
import { StatusBadge } from "@/components/shared/StatusBadge";
import type { PipelineListItem as PipelineListItemType } from "@/types/pipeline";

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
  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-xl cursor-pointer transition-all duration-200 border ${
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
          {pipeline.name}
        </h3>
        <StatusBadge status={pipeline.airflow_status} size="sm" />
      </div>
      <div className="text-xs text-slate-500 font-mono mb-3">
        {pipeline.category}
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
      </div>
    </div>
  );
});
