import { useEffect, useMemo } from "react";
import { usePipelines } from "@/hooks/use-pipelines";
import { useDagSummary } from "@/hooks/use-dag-summary";
import { usePipelineStore } from "@/stores/pipeline-store";
import { PipelineSearch } from "./PipelineSearch";
import { PipelineFilters } from "./PipelineFilters";
import { PipelineListItem } from "./PipelineListItem";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { X } from "lucide-react";
import type { PipelineListItem as PipelineListItemType } from "@/types/pipeline";

interface CategoryGroup {
  category: string;
  pipelines: PipelineListItemType[];
}

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
  const { data: pipelines, isLoading, isError, refetch } = usePipelines(searchQuery);
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
      const group = pipeline.category?.toLowerCase().includes("api") ? "API" : "ETL";
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

  const isFiltered = hasActiveFilters && pipelines && filteredPipelines.length !== pipelines.length;

  return (
    <div className="w-[400px] border-r border-white/5 flex flex-col bg-[#09090b] shrink-0">
      <div className="p-6 border-b border-white/5">
        <h2 className="text-xl font-medium text-white tracking-tight mb-4">
          Pipeline Registry
        </h2>
        <PipelineSearch />
      </div>

      {/* Filter drawer */}
      {filtersOpen && (
        <PipelineFilters availableTeams={availableTeams} availableDags={availableDags} />
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
            Showing {filteredPipelines.length} of {pipelines!.length}
          </span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 custom-scrollbar">
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
            onRetry={() => refetch()}
          />
        )}

        {groupedPipelines.map((group) => (
          <div key={group.category}>
            <div className="sticky top-0 z-10 px-3 pt-4 pb-1.5 bg-[#09090b]">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
                  {group.category}
                </span>
                <span className="text-[10px] font-mono text-slate-600">
                  {group.pipelines.length}
                </span>
                <div className="flex-1 h-px bg-white/5" />
              </div>
            </div>
            <div className="space-y-1">
              {group.pipelines.map((pipeline) => (
                <PipelineListItem
                  key={pipeline.id}
                  pipeline={pipeline}
                  isActive={selectedPipelineId === pipeline.id}
                  onClick={() => setSelectedPipelineId(pipeline.id)}
                />
              ))}
            </div>
          </div>
        ))}

        {pipelines && filteredPipelines.length === 0 && (
          <div className="text-center text-slate-500 text-sm py-8">
            {hasActiveFilters ? "No pipelines match filters" : "No pipelines found"}
          </div>
        )}
      </div>
    </div>
  );
}
