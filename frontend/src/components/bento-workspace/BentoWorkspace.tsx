import { usePipelineDetail } from "@/hooks/use-pipeline-detail";
import { useUpdatePipeline } from "@/hooks/use-update-pipeline";
import { usePipelineStore } from "@/stores/pipeline-store";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { BentoHeader } from "./BentoHeader";
import { LineageTopology } from "./LineageTopology";
import { MetricsCards } from "./MetricsCards";
import { SchemaViewer } from "./SchemaViewer";
import { ConsumeSnippet } from "./ConsumeSnippet";
import { JoinIntelligence } from "./JoinIntelligence";
import { UsageCard } from "./UsageCard";
import { ResourcePerformanceCard } from "./ResourcePerformanceCard";
import { TransformInspectorCard } from "./TransformInspectorCard";
import { isApiPipeline } from "@/lib/utils";

export function BentoWorkspace() {
  const selectedPipelineId = usePipelineStore((s) => s.selectedPipelineId);
  const { data: pipeline, isLoading, error, refetch } = usePipelineDetail(selectedPipelineId);
  const { mutate: updatePipeline, isPending: isSaving } = useUpdatePipeline(selectedPipelineId ?? "");

  if (!selectedPipelineId) {
    return (
      <div data-section="bento-workspace" className="flex-1 flex items-center justify-center text-slate-600">
        <p className="text-sm font-mono">Select a pipeline to explore</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div data-section="bento-workspace" className="flex-1 overflow-y-auto p-8 custom-scrollbar">
        <Skeleton className="h-8 w-64 bg-white/5 mb-2" />
        <Skeleton className="h-5 w-96 bg-white/5 mb-8" />
        <div className="grid grid-cols-12 gap-6">
          <Skeleton className="col-span-12 lg:col-span-8 h-48 bg-white/5 rounded-2xl" />
          <Skeleton className="col-span-12 lg:col-span-4 h-48 bg-white/5 rounded-2xl" />
          <Skeleton className="col-span-12 h-36 bg-white/5 rounded-2xl" />
          <Skeleton className="col-span-12 lg:col-span-7 h-64 bg-white/5 rounded-2xl" />
          <Skeleton className="col-span-12 lg:col-span-5 h-64 bg-white/5 rounded-2xl" />
        </div>
      </div>
    );
  }

  if (error || !pipeline) {
    return (
      <div data-section="bento-workspace" className="flex-1 flex items-center justify-center">
        <ErrorState
          message="Failed to load pipeline details"
          onRetry={refetch}
        />
      </div>
    );
  }

  return (
    <div data-section="bento-workspace" className="flex-1 overflow-y-auto p-8 custom-scrollbar">
      <BentoHeader
        pipeline={pipeline}
        onSaveDescription={(description) =>
          updatePipeline({ description })
        }
        onSaveDocumentation={(documentation) =>
          updatePipeline({ documentation })
        }
        isSaving={isSaving}
        canEdit={pipeline.can_edit}
      />

      <div className="grid grid-cols-12 gap-6 mt-6">
        {/* Row 1: Lineage + Metrics */}
        <LineageTopology pipelineId={pipeline.id} />
        <MetricsCards
          rowsPerDay={pipeline.rows_per_day}
          schedule={pipeline.schedule}
        />

        {/* Row 2: Resource & Performance */}
        {!isApiPipeline(pipeline.pipeline_type) && (
          <ResourcePerformanceCard pipelineId={pipeline.id} />
        )}

        {/* Row 2.5: Execution Plan Tree */}
        {!isApiPipeline(pipeline.pipeline_type) && (
          <TransformInspectorCard pipelineId={pipeline.id} />
        )}

        {/* Row 3: Schema + Usage (left) | Join Intelligence + Consume (right) */}
        <div className="col-span-12 lg:col-span-7 flex flex-col gap-6">
          <SchemaViewer fields={pipeline.fields} />
          <UsageCard etlName={pipeline.task_id ?? pipeline.name} />
        </div>
        <div className="col-span-12 lg:col-span-5 flex flex-col gap-6">
          <JoinIntelligence pipelineId={pipeline.id} />
          <ConsumeSnippet pipelineName={pipeline.name} pipelineType={pipeline.pipeline_type} />
        </div>
      </div>
    </div>
  );
}
