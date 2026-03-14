import { useEffect, useMemo, useRef, useCallback } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Network } from "lucide-react";
import { useSchemaMatrix } from "@/hooks/use-schema-matrix";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { FieldFrequencyRow } from "./FieldFrequencyRow";

/* ── Module-level constants ────────────────────────────────────────── */

const ROW_HEIGHT = 48;

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

export function SchemaMatrixView() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
    refetch,
  } = useSchemaMatrix();
  const scrollRef = useRef<HTMLDivElement>(null);

  const fields = useMemo(
    () => data?.pages.flatMap((p) => p.fields) ?? [],
    [data],
  );
  const total = data?.pages[0]?.total ?? 0;

  const getScrollElement = useCallback(() => scrollRef.current, []);
  const estimateSize = useCallback(() => ROW_HEIGHT, []);
  const measureElement = useCallback(
    (el: Element) => el.getBoundingClientRect().height,
    [],
  );

  const virtualizer = useVirtualizer({
    count: fields.length,
    getScrollElement,
    estimateSize,
    overscan: 15,
    measureElement,
  });

  // Infinite scroll: fetch next page when scrolling near bottom
  const virtualItems = virtualizer.getVirtualItems();
  const lastVirtualItem = virtualItems[virtualItems.length - 1];
  useEffect(() => {
    if (!lastVirtualItem) return;
    if (
      lastVirtualItem.index >= fields.length - 5 &&
      hasNextPage &&
      !isFetchingNextPage
    ) {
      fetchNextPage();
    }
  }, [lastVirtualItem?.index, fields.length, hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (isLoading) {
    return (
      <div data-section="schema-matrix" className="flex-1 flex items-center justify-center">
        <LoadingState />
      </div>
    );
  }

  if (error) {
    return (
      <div data-section="schema-matrix" className="flex-1 flex items-center justify-center">
        <ErrorState message="Failed to load schema matrix" onRetry={refetch} />
      </div>
    );
  }

  if (fields.length === 0) {
    return (
      <div data-section="schema-matrix" className="flex-1 flex items-center justify-center">
        <EmptyState message="No shared fields found across pipelines" />
      </div>
    );
  }

  const totalLabel = useMemo(() => (total > 0 ? total : fields.length), [total, fields.length]);

  return (
    <div ref={scrollRef} data-section="schema-matrix" className="flex-1 overflow-y-auto custom-scrollbar">
      <div className="p-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-indigo-500/10 p-2 rounded-lg border border-indigo-500/20">
              <Network className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-white">Field Frequency Matrix</h1>
              <p className="text-xs text-slate-500 font-mono mt-0.5">
                Fields shared across 2+ pipelines — {totalLabel} fields found
              </p>
            </div>
          </div>
        </div>

        {/* Column Headers */}
        <div className="flex items-center gap-4 px-5 py-2 text-[10px] font-mono uppercase tracking-widest text-slate-600 border-b border-white/5 mb-2">
          <div className="w-48 shrink-0">Field Name</div>
          <div className="w-24 shrink-0">Frequency</div>
          <div className="flex-1">Pipelines</div>
        </div>

        {/* Virtualized Rows */}
        <div style={TOTAL_SIZE_STYLE(virtualizer.getTotalSize())}>
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const row = fields[virtualRow.index];
            return (
              <div
                key={row.field_name}
                ref={virtualizer.measureElement}
                data-index={virtualRow.index}
                style={{
                  ...VIRTUAL_ROW_STYLE,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                <FieldFrequencyRow row={row} />
              </div>
            );
          })}
        </div>

        {isFetchingNextPage && (
          <div className="py-4">
            <LoadingState />
          </div>
        )}
      </div>
    </div>
  );
}
