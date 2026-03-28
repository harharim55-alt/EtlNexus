import { memo } from "react";
import { Star, GitCompareArrows } from "lucide-react";
import type { PipelineListItem as PipelineListItemType } from "@/types/pipeline";
import { stripDummy, formatFreshness, formatCount, formatDateFull } from "@/lib/format";
import { useFavoritesStore } from "@/stores/favorites-store";
import { useComparisonStore } from "@/stores/comparison-store";
import { usePipelineStore } from "@/stores/pipeline-store";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

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
  const isFavorite = useFavoritesStore((s) => s.favoriteIds.includes(pipeline.id));
  const toggleFavorite = useFavoritesStore((s) => s.toggleFavorite);
  const startComparison = useComparisonStore((s) => s.startComparison);
  const selectedPipelineId = usePipelineStore((s) => s.selectedPipelineId);

  const fresh = formatFreshness(pipeline.last_run_at);
  const staleBorder = fresh.stale && fresh.label !== "never"
    ? "border-l-2 border-l-rose-500/30"
    : "";

  return (
    <div
      onClick={onClick}
      className={`group/item p-4 rounded-xl cursor-pointer transition-all duration-200 border ${staleBorder} ${
        isActive
          ? "bg-card border-indigo-500/30 shadow-[0_4px_20px_rgba(0,0,0,0.2)]"
          : "bg-transparent border-transparent hover:bg-hover-bg"
      }`}
    >
      <div className="flex items-start justify-between mb-1">
        <div className="flex items-center gap-1.5 min-w-0">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              toggleFavorite(pipeline.id);
            }}
            className={`shrink-0 transition-colors cursor-pointer ${
              isFavorite
                ? "text-amber-400"
                : "text-transparent hover:text-text-muted"
            }`}
          >
            <Star className="size-3.5" fill={isFavorite ? "currentColor" : "none"} />
          </button>
          <h3
            className={`font-medium text-sm truncate ${
              isActive ? "text-indigo-400" : "text-text-primary"
            }`}
          >
            {stripDummy(pipeline.name)}
          </h3>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {/* Compare button — visible on hover */}
          {selectedPipelineId && selectedPipelineId !== pipeline.id && (
            <Tooltip>
              <TooltipTrigger
                className="opacity-0 group-hover/item:opacity-100 transition-opacity cursor-pointer text-text-muted hover:text-indigo-400 mt-1"
                onClick={(e: React.MouseEvent) => {
                  e.stopPropagation();
                  startComparison(selectedPipelineId, pipeline.id);
                }}
              >
                <GitCompareArrows className="size-3.5" />
              </TooltipTrigger>
              <TooltipContent
                side="right"
                className="bg-card border-border-prominent text-foreground text-xs font-medium"
              >
                Compare with selected pipeline
              </TooltipContent>
            </Tooltip>
          )}

          <Tooltip>
            <TooltipTrigger className="shrink-0 mt-1.5 cursor-default">
              <span className={`block h-2 w-2 rounded-full ${dot.color}`} />
            </TooltipTrigger>
            <TooltipContent
              side="right"
              className="bg-card border-border-prominent text-foreground text-xs font-medium"
            >
              <div className="flex flex-col gap-0.5">
                <span>{dot.title}</span>
                {pipeline.execution_date && (
                  <span className="text-text-secondary">
                    Last run: {formatDateFull(pipeline.execution_date)}
                  </span>
                )}
              </div>
            </TooltipContent>
          </Tooltip>
        </div>
      </div>
      <div className="text-xs text-text-muted font-mono mb-3">
        {pipeline.pipeline_type === "api" ? "API" : "ETL"}
      </div>
      <div className="flex gap-2 text-[10px] font-mono">
        {pipeline.schedule && (
          <span className="px-2 py-0.5 rounded bg-hover-bg text-text-secondary border border-border">
            {pipeline.schedule}
          </span>
        )}
        {pipeline.rows_per_day && (
          <span className="px-2 py-0.5 rounded bg-hover-bg text-text-secondary border border-border">
            {isNaN(Number(pipeline.rows_per_day))
              ? pipeline.rows_per_day
              : `${formatCount(Number(pipeline.rows_per_day))} rows/day`}
          </span>
        )}
        <span className={`px-2 py-0.5 rounded bg-hover-bg border border-border ${fresh.className}`}>
          {fresh.label === "never" ? "no runs" : fresh.label}
        </span>
      </div>
    </div>
  );
});
