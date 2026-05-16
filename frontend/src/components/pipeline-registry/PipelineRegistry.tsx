import { useEffect, useMemo, useCallback } from "react";
import { usePipelines } from "@/hooks/use-pipelines";
import { useDagSummary } from "@/hooks/use-dag-summary";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useFavoritesStore } from "@/stores/favorites-store";
import { PipelineSearch } from "./PipelineSearch";
import { PipelineFilters } from "./PipelineFilters";
import { PipelineListContent } from "./PipelineListContent";

import { X } from "lucide-react";
import type { PipelineListItem as PipelineListItemType } from "@/types/pipeline";
import type { PipelineFilterParams } from "@/api/pipelines";

/* ── Types ────────────────────────────────────────────────────────── */

interface CategoryGroup {
  category: string;
  pipelines: PipelineListItemType[];
}

/* ── Component ─────────────────────────────────────────────────────── */

export function PipelineRegistry() {
  const {
    searchQuery,
    selectedPipelineId,
    setSelectedPipelineId,
    filtersOpen,
    teamFilters,
    dagFilters,
    statusFilters,
    tagFilters,
    clearAllFilters,
  } = usePipelineStore();
  // Build server-side filter params from store sets
  const serverFilters = useMemo<PipelineFilterParams | undefined>(() => {
    const f: PipelineFilterParams = {};
    if (teamFilters.size > 0) f.team = Array.from(teamFilters);
    if (dagFilters.size > 0) f.dag_id = Array.from(dagFilters);
    if (statusFilters.size > 0) f.status = Array.from(statusFilters);
    return Object.keys(f).length > 0 ? f : undefined;
  }, [teamFilters, dagFilters, statusFilters]);

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    refetch,
  } = usePipelines(searchQuery, serverFilters);
  const pipelines = useMemo(
    () => data?.pages.flatMap((p) => p.items) ?? [],
    [data],
  );
  const { data: dagSummary } = useDagSummary();

  const hasActiveFilters =
    teamFilters.size > 0 || dagFilters.size > 0 || statusFilters.size > 0 || tagFilters.size > 0;

  // Build DAG -> pipeline ID mapping from DAG summary
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

  const availableTags = useMemo(() => {
    if (!pipelines) return [];
    const tags = new Set<string>();
    for (const p of pipelines) {
      for (const t of (p.tags ?? [])) {
        tags.add(t.name);
      }
    }
    return Array.from(tags).sort();
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
      if (tagFilters.size > 0) {
        const pipelineTags = new Set((p.tags ?? []).map((t) => t.name));
        let hasAnyTag = false;
        for (const tag of tagFilters) {
          if (pipelineTags.has(tag)) { hasAnyTag = true; break; }
        }
        if (!hasAnyTag) return false;
      }
      return true;
    });
  }, [pipelines, teamFilters, dagFilters, statusFilters, tagFilters, dagToPipelineIds, hasActiveFilters]);

  const favoriteIds = useFavoritesStore((s) => s.favoriteIds);

  const groupedPipelines = useMemo<CategoryGroup[]>(() => {
    if (!filteredPipelines.length) return [];

    const result: CategoryGroup[] = [];

    // Favorites group at top
    const favSet = new Set(favoriteIds);
    const favPipelines = filteredPipelines.filter((p) => favSet.has(p.id));
    if (favPipelines.length > 0) {
      result.push({ category: "\u2605 Favorites", pipelines: favPipelines });
    }

    // Group by team
    const groups = new Map<string, PipelineListItemType[]>();
    for (const pipeline of filteredPipelines) {
      const group = pipeline.team || "Unassigned";
      if (!groups.has(group)) {
        groups.set(group, []);
      }
      groups.get(group)!.push(pipeline);
    }

    for (const items of groups.values()) {
      items.sort((a, b) => a.name.localeCompare(b.name));
    }

    const sorted = Array.from(groups.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([category, pipelines]) => ({ category, pipelines }));

    result.push(...sorted);
    return result;
  }, [filteredPipelines, favoriteIds]);

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
    if (tagFilters.size > 0) parts.push(Array.from(tagFilters).join(", "));
    return parts.join(" \u00b7 ");
  }, [hasActiveFilters, teamFilters, dagFilters, tagFilters]);

  const isFiltered = hasActiveFilters && pipelines.length > 0 && filteredPipelines.length !== pipelines.length;

  const handleSelectPipeline = useCallback(
    (id: string) => setSelectedPipelineId(id),
    [setSelectedPipelineId],
  );

  const handleRetry = useCallback(() => refetch(), [refetch]);

  return (
    <div data-section="pipeline-registry" className="w-[400px] border-r border-border flex flex-col bg-background shrink-0">
      <div className="p-6 border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-medium text-foreground tracking-tight">
            Pipeline Registry
          </h2>
        </div>
        <PipelineSearch />
      </div>

      {/* Filter drawer */}
      <div
        className="grid transition-all duration-200 border-b"
        style={{
          gridTemplateRows: filtersOpen ? "1fr" : "0fr",
          opacity: filtersOpen ? 1 : 0,
          borderColor: filtersOpen ? "rgba(255,255,255,0.05)" : "transparent",
        }}
      >
        <div className="overflow-hidden">
          <PipelineFilters availableTeams={availableTeams} availableDags={availableDags} availableTags={availableTags} />
        </div>
      </div>

      {/* Active filter summary strip (when drawer closed) */}
      {!filtersOpen && hasActiveFilters && (
        <div className="px-6 py-2 border-b border-border flex items-center gap-2 animate-in fade-in duration-150">
          <span className="text-[10px] font-mono text-text-muted truncate flex-1">
            <span className="text-text-faint">Filtered:</span>{" "}
            <span className="text-indigo-400">{filterSummary}</span>
          </span>
          <button
            type="button"
            onClick={clearAllFilters}
            className="text-text-faint hover:text-text-secondary transition-colors cursor-pointer shrink-0"
          >
            <X className="size-3" />
          </button>
        </div>
      )}

      {/* Result count when filtered */}
      {isFiltered && (
        <div className="px-6 py-1.5">
          <span className="text-[10px] font-mono text-text-faint">
            Showing {filteredPipelines.length} of {pipelines.length}
          </span>
        </div>
      )}

      <PipelineListContent
        groupedPipelines={groupedPipelines}
        selectedPipelineId={selectedPipelineId}
        onSelectPipeline={handleSelectPipeline}
        isLoading={isLoading}
        isError={isError}
        onRetry={handleRetry}
        totalCount={pipelines.length}
        filteredCount={filteredPipelines.length}
        hasNextPage={hasNextPage ?? false}
        isFetchingNextPage={isFetchingNextPage}
        fetchNextPage={fetchNextPage}
      />
    </div>
  );
}
