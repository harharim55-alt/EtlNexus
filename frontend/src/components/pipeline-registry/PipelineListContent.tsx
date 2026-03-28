import { useRef, useEffect, useCallback, useMemo } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { PipelineListItem } from "./PipelineListItem";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import type { PipelineListItem as PipelineListItemType } from "@/types/pipeline";

/* ── Module-level constants ────────────────────────────────────────── */

const VIRTUAL_ROW_STYLE: React.CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  width: "100%",
};

const TOTAL_SIZE_STYLE = (height: number): React.CSSProperties => ({
  height: `${height}px`,
  position: "relative",
});

/* ── Types ────────────────────────────────────────────────────────── */

interface CategoryGroup {
  category: string;
  pipelines: PipelineListItemType[];
}

type FlatItem =
  | { type: "header"; category: string; count: number }
  | { type: "pipeline"; pipeline: PipelineListItemType };

/* ── Props ────────────────────────────────────────────────────────── */

interface PipelineListContentProps {
  groupedPipelines: CategoryGroup[];
  selectedPipelineId: string | null;
  onSelectPipeline: (id: string) => void;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  totalCount: number;
  filteredCount: number;
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
}

/* ── Component ─────────────────────────────────────────────────────── */

export function PipelineListContent({
  groupedPipelines,
  selectedPipelineId,
  onSelectPipeline,
  isLoading,
  isError,
  onRetry,
  totalCount,
  filteredCount,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
}: PipelineListContentProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const flatItems = useMemo<FlatItem[]>(() => {
    const items: FlatItem[] = [];
    for (const group of groupedPipelines) {
      items.push({ type: "header", category: group.category, count: group.pipelines.length });
      for (const pipeline of group.pipelines) {
        items.push({ type: "pipeline", pipeline });
      }
    }
    return items;
  }, [groupedPipelines]);

  const handleSelectPipeline = useCallback(
    (id: string) => onSelectPipeline(id),
    [onSelectPipeline],
  );

  const handleRetry = useCallback(() => onRetry(), [onRetry]);

  const estimateSize = useCallback(
    (index: number) => (flatItems[index].type === "header" ? 40 : 108),
    [flatItems],
  );

  const virtualizer = useVirtualizer({
    count: flatItems.length,
    getScrollElement: () => scrollRef.current,
    estimateSize,
    overscan: 10,
    measureElement: (el) => el.getBoundingClientRect().height,
  });

  // Infinite scroll: fetch next page when scrolling near bottom
  const virtualItems = virtualizer.getVirtualItems();
  const lastVirtualItem = virtualItems[virtualItems.length - 1];
  useEffect(() => {
    if (!lastVirtualItem) return;
    if (
      lastVirtualItem.index >= flatItems.length - 5 &&
      hasNextPage &&
      !isFetchingNextPage
    ) {
      fetchNextPage();
    }
  }, [lastVirtualItem?.index, flatItems.length, hasNextPage, isFetchingNextPage, fetchNextPage]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 custom-scrollbar">
      {isLoading && (
        <div className="space-y-3 p-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl bg-hover-bg" />
          ))}
        </div>
      )}

      {isError && (
        <ErrorState
          message="Failed to load pipelines"
          onRetry={handleRetry}
        />
      )}

      {flatItems.length > 0 && (
        <div style={TOTAL_SIZE_STYLE(virtualizer.getTotalSize())}>
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const item = flatItems[virtualRow.index];
            return (
              <div
                key={virtualRow.index}
                ref={virtualizer.measureElement}
                data-index={virtualRow.index}
                style={{
                  ...VIRTUAL_ROW_STYLE,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                {item.type === "header" ? (
                  <div className="px-3 pt-4 pb-1.5 bg-background">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted">
                        {item.category}
                      </span>
                      <span className="text-[10px] font-mono text-text-faint">
                        {item.count}
                      </span>
                      <div className="flex-1 h-px bg-hover-bg" />
                    </div>
                  </div>
                ) : (
                  <PipelineListItem
                    pipeline={item.pipeline}
                    isActive={selectedPipelineId === item.pipeline.id}
                    onClick={() => handleSelectPipeline(item.pipeline.id)}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}

      {isFetchingNextPage && (
        <div className="py-4">
          <LoadingState />
        </div>
      )}

      {!isLoading && totalCount > 0 && filteredCount === 0 && (
        <div className="text-center text-text-muted text-sm py-8">
          No pipelines match filters
        </div>
      )}

      {!isLoading && totalCount === 0 && (
        <div className="text-center text-text-muted text-sm py-8">
          No pipelines found
        </div>
      )}
    </div>
  );
}
