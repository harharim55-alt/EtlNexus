import { memo } from "react";
import { Star } from "lucide-react";
import type { PipelineListItem as PipelineListItemType } from "@/types/pipeline";
import { stripDummy } from "@/lib/format";
import { useFavoritesStore } from "@/stores/favorites-store";

interface DataProductListItemProps {
  product: PipelineListItemType;
  isActive: boolean;
  onClick: () => void;
}

export const DataProductListItem = memo(function DataProductListItem({
  product,
  isActive,
  onClick,
}: DataProductListItemProps) {
  const isFavorite = useFavoritesStore((s) => s.favoriteIds.includes(product.id));
  const toggleFavorite = useFavoritesStore((s) => s.toggleFavorite);

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
              toggleFavorite(product.id);
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
            {stripDummy(product.name)}
          </h3>
        </div>
      </div>

      {product.team && (
        <div className="text-xs text-emerald-400/70 font-mono mb-3 ml-5">
          {product.team}
        </div>
      )}

      <div className="flex gap-2 text-[10px] font-mono flex-wrap ml-5">
        {product.schedule && (
          <span className="px-2 py-0.5 rounded bg-hover-bg text-text-secondary border border-border">
            {product.schedule}
          </span>
        )}
        {(product.tags ?? []).slice(0, 3).map((tag) => (
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
