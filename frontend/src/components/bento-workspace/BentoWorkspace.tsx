import { usePipelineDetail } from "@/hooks/use-pipeline-detail";
import { useUpdatePipeline } from "@/hooks/use-update-pipeline";
import { usePipelineStore } from "@/stores/pipeline-store";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { BentoHeader } from "./BentoHeader";
import { DocumentationPreview } from "./DocumentationPreview";
import { LineageTopology } from "./LineageTopology";
import { SchemaViewer } from "./SchemaViewer";
import { ConsumeSnippet } from "./ConsumeSnippet";
import { UsageCard } from "./UsageCard";
import { ResourcePerformanceCard } from "./ResourcePerformanceCard";
import { TransformInspectorCard } from "./TransformInspectorCard";
import { isApiPipeline } from "@/lib/utils";
import { stripDummy } from "@/lib/format";

export function BentoWorkspace() {
  const selectedPipelineId = usePipelineStore((s) => s.selectedPipelineId);
  const { data: pipeline, isLoading, error, refetch } = usePipelineDetail(selectedPipelineId);
  const { mutate: updatePipeline, isPending: isSaving } = useUpdatePipeline(selectedPipelineId ?? "");

  if (!selectedPipelineId) {
    return (
      <div data-section="bento-workspace" className="flex-1 flex items-center justify-center text-text-faint">
        <p className="text-sm font-mono">Select a pipeline to explore</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div data-section="bento-workspace" className="flex-1 overflow-y-auto p-8 custom-scrollbar">
        <Skeleton className="h-8 w-64 bg-hover-bg mb-2" />
        <Skeleton className="h-5 w-96 bg-hover-bg mb-8" />
        <div className="grid grid-cols-12 gap-6">
          <Skeleton className="col-span-12 h-24 bg-hover-bg rounded-2xl" />
          <Skeleton className="col-span-12 lg:col-span-8 h-48 bg-hover-bg rounded-2xl" />
          <Skeleton className="col-span-12 lg:col-span-4 h-48 bg-hover-bg rounded-2xl" />
          <Skeleton className="col-span-12 lg:col-span-7 h-64 bg-hover-bg rounded-2xl" />
          <Skeleton className="col-span-12 lg:col-span-5 h-64 bg-hover-bg rounded-2xl" />
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
        onSaveDescription={(description) => updatePipeline({ description })}
        onSaveDocumentation={(documentation) => updatePipeline({ documentation })}
        onUpdate={(updates) => updatePipeline(updates as Record<string, unknown>)}
        isSaving={isSaving}
        canEdit={pipeline.can_edit}
      />

      <div className="grid grid-cols-12 gap-6 mt-6">
        {/* Documentation preview */}
        <DocumentationPreview
          pipelineId={pipeline.id}
          pipelineName={stripDummy(pipeline.name)}
          documentation={pipeline.documentation}
          onSave={(doc) => updatePipeline({ documentation: doc })}
          isSaving={isSaving}
          canEdit={pipeline.can_edit}
        />

        {/* Import & Consume */}
        <div className="col-span-12">
          <ConsumeSnippet
            pipelineName={stripDummy(pipeline.name)}
            pipelineType={pipeline.pipeline_type}
            team={pipeline.team}
            importSnippet={pipeline.import_snippet}
          />
        </div>

        {isApiPipeline(pipeline.pipeline_type) ? (
          <>
            {pipeline.topology_enabled && (
              <LineageTopology pipelineId={pipeline.id} fullWidth />
            )}
            <div className="col-span-12 lg:col-span-7">
              <SchemaViewer
                fields={pipeline.fields}
                pipelineId={pipeline.id}
                canEdit={pipeline.can_edit}
                schemaManuallyEdited={pipeline.schema_manually_edited}
              />
            </div>
            <div className="col-span-12 lg:col-span-5">
              <UsageCard etlName={pipeline.task_id ?? pipeline.name} />
            </div>
          </>
        ) : (
          <>
            {pipeline.topology_enabled && (
              <LineageTopology pipelineId={pipeline.id} fullWidth />
            )}
            <ResourcePerformanceCard pipelineId={pipeline.id} />
            <TransformInspectorCard pipelineId={pipeline.id} />
            <div className="col-span-12 lg:col-span-7">
              <SchemaViewer
                fields={pipeline.fields}
                pipelineId={pipeline.id}
                canEdit={pipeline.can_edit}
                schemaManuallyEdited={pipeline.schema_manually_edited}
              />
            </div>
            <div className="col-span-12 lg:col-span-5">
              <UsageCard etlName={pipeline.task_id ?? pipeline.name} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
