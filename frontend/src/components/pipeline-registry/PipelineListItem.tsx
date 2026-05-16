import { memo } from "react";
import { Star, GitCompareArrows, PackagePlus } from "lucide-react";
import type { PipelineListItem as PipelineListItemType } from "@/types/pipeline";
import { stripDummy } from "@/lib/format";
import { useFavoritesStore } from "@/stores/favorites-store";
import { useComparisonStore } from "@/stores/comparison-store";
import { usePipelineStore } from "@/stores/pipeline-store";
import { usePromoteToDataProduct } from "@/hooks/use-promote-to-data-product";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

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
  const isFavorite = useFavoritesStore((s) => s.favoriteIds.includes(pipeline.id));
  const toggleFavorite = useFavoritesStore((s) => s.toggleFavorite);
  const startComparison = useComparisonStore((s) => s.startComparison);
  const selectedPipelineId = usePipelineStore((s) => s.selectedPipelineId);
  const promote = usePromoteToDataProduct();

  return (
    <div
      onClick={onClick}
      className={`group/item p-4 rounded-xl cursor-pointer transition-all duration-200 border ${
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
          {/* Promote to Data Product — ETL pipelines only */}
          {!pipeline.is_data_product && (
            <Tooltip>
              <TooltipTrigger
                className="opacity-0 group-hover/item:opacity-100 transition-opacity cursor-pointer text-text-muted hover:text-emerald-400 mt-1"
                onClick={(e: React.MouseEvent) => {
                  e.stopPropagation();
                  promote.mutate(pipeline.id);
                }}
              >
                <PackagePlus className="size-3.5" />
              </TooltipTrigger>
              <TooltipContent
                side="right"
                className="bg-card border-border-prominent text-foreground text-xs font-medium"
              >
                Import to Data Products
              </TooltipContent>
            </Tooltip>
          )}
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
        </div>
      </div>

      <div className="text-xs text-text-muted font-mono mb-3">
        {pipeline.pipeline_type === "api" ? "API" : "ETL"}
        {pipeline.team && <span className="ml-2 text-emerald-400/70">{pipeline.team}</span>}
      </div>

      <div className="flex gap-2 text-[10px] font-mono flex-wrap">
        {(pipeline.schedule || pipeline.schedule_type) && (
          <span className="px-2 py-0.5 rounded bg-hover-bg text-text-secondary border border-border">
            {pipeline.schedule ?? pipeline.schedule_type}
          </span>
        )}
        {(pipeline.tags ?? []).slice(0, 3).map((tag) => (
          <span
            key={tag.id}
            className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20"
          >
            {tag.name}
          </span>
        ))}
      </div>
    </div>
  );
});
