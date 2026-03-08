import { useEffect } from "react";
import { usePipelines } from "@/hooks/use-pipelines";
import { usePipelineStore } from "@/stores/pipeline-store";
import { PipelineSearch } from "./PipelineSearch";
import { PipelineListItem } from "./PipelineListItem";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";

export function PipelineRegistry() {
  const { searchQuery, selectedPipelineId, setSelectedPipelineId } =
    usePipelineStore();
  const { data: pipelines, isLoading, isError, refetch } = usePipelines(searchQuery);

  // Auto-select the first pipeline when the list loads and nothing is selected
  useEffect(() => {
    if (pipelines && pipelines.length > 0 && !selectedPipelineId) {
      setSelectedPipelineId(pipelines[0].id);
    }
  }, [pipelines, selectedPipelineId, setSelectedPipelineId]);

  return (
    <div className="w-[400px] border-r border-white/5 flex flex-col bg-[#09090b] shrink-0">
      <div className="p-6 border-b border-white/5">
        <h2 className="text-xl font-medium text-white tracking-tight mb-4">
          Pipeline Registry
        </h2>
        <PipelineSearch />
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-1 custom-scrollbar">
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

        {pipelines?.map((pipeline) => (
          <PipelineListItem
            key={pipeline.id}
            pipeline={pipeline}
            isActive={selectedPipelineId === pipeline.id}
            onClick={() => setSelectedPipelineId(pipeline.id)}
          />
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
