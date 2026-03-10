import { useEffect, useMemo } from "react";
import { usePipelines } from "@/hooks/use-pipelines";
import { usePipelineStore } from "@/stores/pipeline-store";
import { PipelineSearch } from "./PipelineSearch";
import { PipelineListItem } from "./PipelineListItem";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import type { PipelineListItem as PipelineListItemType } from "@/types/pipeline";

interface CategoryGroup {
  category: string;
  pipelines: PipelineListItemType[];
}

export function PipelineRegistry() {
  const { searchQuery, selectedPipelineId, setSelectedPipelineId } =
    usePipelineStore();
  const { data: pipelines, isLoading, isError, refetch } = usePipelines(searchQuery);

  const groupedPipelines = useMemo<CategoryGroup[]>(() => {
    if (!pipelines) return [];

    const groups = new Map<string, PipelineListItemType[]>();

    for (const pipeline of pipelines) {
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
  }, [pipelines]);

  // Auto-select the first pipeline when the list loads and nothing is selected
  useEffect(() => {
    if (groupedPipelines.length > 0 && !selectedPipelineId) {
      setSelectedPipelineId(groupedPipelines[0].pipelines[0].id);
    }
  }, [groupedPipelines, selectedPipelineId, setSelectedPipelineId]);

  return (
    <div className="w-[400px] border-r border-white/5 flex flex-col bg-[#09090b] shrink-0">
      <div className="p-6 border-b border-white/5">
        <h2 className="text-xl font-medium text-white tracking-tight mb-4">
          Pipeline Registry
        </h2>
        <PipelineSearch />
      </div>

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

        {pipelines && pipelines.length === 0 && (
          <div className="text-center text-slate-500 text-sm py-8">
            No pipelines found
          </div>
        )}
      </div>
    </div>
  );
}
