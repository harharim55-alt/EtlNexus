import { useEffect, useMemo, useRef, useCallback } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { usePipelines } from "@/hooks/use-pipelines";
import { useDagSummary } from "@/hooks/use-dag-summary";
import { usePipelineStore } from "@/stores/pipeline-store";
import { PipelineSearch } from "./PipelineSearch";
import { PipelineFilters } from "./PipelineFilters";
import { PipelineListItem } from "./PipelineListItem";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { X } from "lucide-react";
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

interface CategoryGroup {
  category: string;
  pipelines: PipelineListItemType[];
}

type FlatItem =
  | { type: "header"; category: string; count: number }
  | { type: "pipeline"; pipeline: PipelineListItemType };

export function PipelineRegistry() {
  const {
    searchQuery,
    selectedPipelineId,
    setSelectedPipelineId,
    filtersOpen,
    teamFilters,
    dagFilters,
    statusFilters,
    clearAllFilters,
  } = usePipelineStore();
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    refetch,
  } = usePipelines(searchQuery);
  const pipelines = useMemo(
    () => data?.pages.flatMap((p) => p.items) ?? [],
    [data],
  );
  const { data: dagSummary } = useDagSummary();

  const hasActiveFilters =
    teamFilters.size > 0 || dagFilters.size > 0 || statusFilters.size > 0;

  // Build DAG → pipeline ID mapping from DAG summary
  const dagToPipelineIds = useMemo(() => {
    if (!dagSummary) return new Map<string, Set<string>>();
    const map = new Map<string, Set<string>>();
    for (const dag of dagSummary.dags) {
      const ids = new Set<string>();
      for (const task of dag.tasks) {
        if (task.pipeline_id) ids.add(task.pipeline_id);
      }
      map.set(dag.dag_id, ids);
    }
    return map;
  }, [dagSummary]);

  // Derive available filter options from data
  const availableTeams = useMemo(() => {
    if (!pipelines) return [];
    const teams = new Set<string>();
    for (const p of pipelines) {
      if (p.team) teams.add(p.team);
    }
    return Array.from(teams).sort();
  }, [pipelines]);

  const availableDags = useMemo(() => {
    if (!dagSummary) return [];
    return dagSummary.dags.map((d) => d.dag_id).sort();
  }, [dagSummary]);

  const availableStatuses = useMemo(() => {
    if (!pipelines) return [];
    const statuses = new Set<string>();
    for (const p of pipelines) {
      if (p.airflow_status) statuses.add(p.airflow_status);
    }
    return Array.from(statuses);
  }, [pipelines]);

  // Apply client-side filters
  const filteredPipelines = useMemo(() => {
    if (!pipelines) return [];
    if (!hasActiveFilters) return pipelines;

    return pipelines.filter((p) => {
      if (teamFilters.size > 0 && (!p.team || !teamFilters.has(p.team))) return false;
      if (statusFilters.size > 0 && !statusFilters.has(p.airflow_status)) return false;
      if (dagFilters.size > 0) {
        let inAnyDag = false;
        for (const dagId of dagFilters) {
          if (dagToPipelineIds.get(dagId)?.has(p.id)) {
            inAnyDag = true;
            break;
          }
        }
        if (!inAnyDag) return false;
      }
      return true;
    });
  }, [pipelines, teamFilters, dagFilters, statusFilters, dagToPipelineIds, hasActiveFilters]);

  const groupedPipelines = useMemo<CategoryGroup[]>(() => {
    if (!filteredPipelines.length) return [];

    const groups = new Map<string, PipelineListItemType[]>();

    for (const pipeline of filteredPipelines) {
      const group = pipeline.pipeline_type === "api" ? "API" : "ETL";
      if (!groups.has(group)) {
        groups.set(group, []);
      }
      groups.get(group)!.push(pipeline);
    }

    for (const items of groups.values()) {
      items.sort((a, b) => a.name.localeCompare(b.name));
    }

    return Array.from(groups.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([category, pipelines]) => ({ category, pipelines }));
  }, [filteredPipelines]);

  // Auto-select first pipeline when list loads and nothing selected
  useEffect(() => {
    if (groupedPipelines.length > 0 && !selectedPipelineId) {
      setSelectedPipelineId(groupedPipelines[0].pipelines[0].id);
    }
  }, [groupedPipelines, selectedPipelineId, setSelectedPipelineId]);

  // Re-select if current selection is filtered out
  useEffect(() => {
    if (!selectedPipelineId || !filteredPipelines.length) return;
    const stillVisible = filteredPipelines.some((p) => p.id === selectedPipelineId);
    if (!stillVisible) {
      setSelectedPipelineId(filteredPipelines[0].id);
    }
  }, [filteredPipelines, selectedPipelineId, setSelectedPipelineId]);

  // Build active filter summary text
  const filterSummary = useMemo(() => {
    if (!hasActiveFilters) return null;
    const parts: string[] = [];
    if (teamFilters.size > 0) parts.push(Array.from(teamFilters).join(", "));
    if (dagFilters.size > 0)
      parts.push(
        Array.from(dagFilters)
          .map((d) =>
            d
              .split("_")
              .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
              .join(" "),
          )
          .join(", "),
      );
    if (statusFilters.size > 0) parts.push(Array.from(statusFilters).join(", "));
    return parts.join(" \u00b7 ");
  }, [hasActiveFilters, teamFilters, dagFilters, statusFilters]);

  const isFiltered = hasActiveFilters && pipelines.length > 0 && filteredPipelines.length !== pipelines.length;

  // Flatten grouped pipelines into a single virtual list
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

  const scrollRef = useRef<HTMLDivElement>(null);

  const handleSelectPipeline = useCallback(
    (id: string) => setSelectedPipelineId(id),
    [setSelectedPipelineId],
  );

  const handleRetry = useCallback(() => refetch(), [refetch]);

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
    <div data-section="pipeline-registry" className="w-[400px] border-r border-white/5 flex flex-col bg-[#09090b] shrink-0">
      <div className="p-6 border-b border-white/5">
        <h2 className="text-xl font-medium text-white tracking-tight mb-4">
          Pipeline Registry
        </h2>
        <PipelineSearch />
      </div>

      {/* Filter drawer */}
      {filtersOpen && (
        <PipelineFilters availableTeams={availableTeams} availableDags={availableDags} availableStatuses={availableStatuses} />
      )}

      {/* Active filter summary strip (when drawer closed) */}
      {!filtersOpen && hasActiveFilters && (
        <div className="px-6 py-2 border-b border-white/5 flex items-center gap-2 animate-in fade-in duration-150">
          <span className="text-[10px] font-mono text-slate-500 truncate flex-1">
            <span className="text-slate-600">Filtered:</span>{" "}
            <span className="text-indigo-400">{filterSummary}</span>
          </span>
          <button
            type="button"
            onClick={clearAllFilters}
            className="text-slate-600 hover:text-slate-400 transition-colors cursor-pointer shrink-0"
          >
            <X className="size-3" />
          </button>
        </div>
      )}

      {/* Result count when filtered */}
      {isFiltered && (
        <div className="px-6 py-1.5">
          <span className="text-[10px] font-mono text-slate-600">
            Showing {filteredPipelines.length} of {pipelines.length}
          </span>
        </div>
      )}

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 custom-scrollbar">
        {isLoading && (
          <div className="space-y-3 p-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl bg-white/5" />
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
                    <div className="px-3 pt-4 pb-1.5 bg-[#09090b]">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
                          {item.category}
                        </span>
                        <span className="text-[10px] font-mono text-slate-600">
                          {item.count}
                        </span>
                        <div className="flex-1 h-px bg-white/5" />
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

        {!isLoading && pipelines.length > 0 && filteredPipelines.length === 0 && (
          <div className="text-center text-slate-500 text-sm py-8">
            No pipelines match filters
          </div>
        )}

        {!isLoading && pipelines.length === 0 && (
          <div className="text-center text-slate-500 text-sm py-8">
            No pipelines found
          </div>
        )}
      </div>
    </div>
  );
}
