import { useEffect, useMemo, useRef, useCallback, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Download, Network, Search } from "lucide-react";
import { useSchemaMatrix } from "@/hooks/use-schema-matrix";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { downloadAsCSV } from "@/lib/export";
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
  const [searchInput, setSearchInput] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchInput), 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
    refetch,
  } = useSchemaMatrix(debouncedQuery);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fields = useMemo(
    () => data?.pages.flatMap((p) => p.fields) ?? [],
    [data],
  );
  const total = data?.pages[0]?.total ?? 0;
  const totalLabel = useMemo(() => (total > 0 ? total : fields.length), [total, fields.length]);

  const getScrollElement = useCallback(() => scrollRef.current, []);
  const estimateSize = useCallback(() => ROW_HEIGHT, []);
  const measureElement = useCallback(
    (el: Element) => el.getBoundingClientRect().height,
    [],
  );

  const handleExportCSV = useCallback(() => {
    const rows = fields.map((f) => ({
      field_name: f.field_name,
      frequency: f.frequency,
      pipelines: f.pipelines.map((p) => p.pipeline_name).join(", "),
    }));
    downloadAsCSV(rows, "schema-matrix");
  }, [fields]);

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

  return (
    <div ref={scrollRef} data-section="schema-matrix" className="flex-1 overflow-y-auto custom-scrollbar">
      <div className="p-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-indigo-500/10 p-2 rounded-lg border border-indigo-500/20">
              <Network className="w-5 h-5 text-indigo-400" />
            </div>
            <div className="flex-1">
              <h1 className="text-xl font-semibold text-foreground">Field Frequency Matrix</h1>
              <p className="text-xs text-text-muted font-mono mt-0.5">
                Fields shared across 2+ pipelines — {totalLabel} fields found
              </p>
            </div>
            <Tooltip>
              <TooltipTrigger
                className="p-1.5 text-text-muted hover:text-foreground rounded-lg transition-colors cursor-pointer"
                onClick={handleExportCSV}
              >
                <Download className="size-4" />
              </TooltipTrigger>
              <TooltipContent>Export CSV</TooltipContent>
            </Tooltip>
          </div>

          {/* Search Input */}
          <div className="relative mt-4 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
            <input
              type="text"
              placeholder="Search fields..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-hover-bg border border-border-prominent rounded-lg text-text-primary placeholder:text-text-faint focus:outline-none focus:border-indigo-500/30 transition-colors"
            />
          </div>
        </div>

        {/* Column Headers */}
        <div className="flex items-center gap-4 px-5 py-2 text-[10px] font-mono uppercase tracking-widest text-text-faint border-b border-border mb-2">
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
