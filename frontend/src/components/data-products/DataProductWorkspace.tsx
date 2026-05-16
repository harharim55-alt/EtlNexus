import { useMemo } from "react";
import { usePipelineDetail } from "@/hooks/use-pipeline-detail";
import { useUpdatePipeline } from "@/hooks/use-update-pipeline";
import { usePipelineLogs } from "@/hooks/use-pipeline-logs";
import { useDataProductStore } from "@/stores/data-product-store";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { BentoHeader } from "@/components/bento-workspace/BentoHeader";
import { DocumentationPreview } from "@/components/bento-workspace/DocumentationPreview";
import { LineageTopology } from "@/components/bento-workspace/LineageTopology";
import { SchemaViewer } from "@/components/bento-workspace/SchemaViewer";
import { UsageCard } from "@/components/bento-workspace/UsageCard";
import { DataStructureCard } from "@/components/bento-workspace/DataStructureCard";
import { stripDummy } from "@/lib/format";

export function DataProductWorkspace() {
  const selectedProductId = useDataProductStore((s) => s.selectedProductId);
  const { data: pipeline, isLoading, error, refetch } = usePipelineDetail(selectedProductId);
  const { mutate: updatePipeline, isPending: isSaving } = useUpdatePipeline(selectedProductId ?? "");
  const { data: logsData } = usePipelineLogs(selectedProductId);

  const networkNames = useMemo(() => {
    if (!logsData?.items) return [];
    const names = new Set<string>();
    for (const log of logsData.items) {
      for (const n of log.networks) {
        if (n.network_name) names.add(n.network_name);
      }
    }
    return Array.from(names);
  }, [logsData]);

  if (!selectedProductId) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-faint">
        <p className="text-sm font-mono">Select a data product to explore</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
        <Skeleton className="h-8 w-64 bg-hover-bg mb-2" />
        <Skeleton className="h-5 w-96 bg-hover-bg mb-8" />
        <div className="grid grid-cols-12 gap-6">
          <Skeleton className="col-span-12 h-24 bg-hover-bg rounded-2xl" />
          <Skeleton className="col-span-12 h-48 bg-hover-bg rounded-2xl" />
          <Skeleton className="col-span-12 lg:col-span-7 h-64 bg-hover-bg rounded-2xl" />
        </div>
      </div>
    );
  }

  if (error || !pipeline) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <ErrorState message="Failed to load data product" onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
      <BentoHeader
        pipeline={pipeline}
        onSaveDescription={(description) => updatePipeline({ description })}
        onSaveDocumentation={(documentation) => updatePipeline({ documentation })}
        onUpdate={(updates) => updatePipeline(updates as Record<string, unknown>)}
        isSaving={isSaving}
        canEdit={pipeline.can_edit}
      />

      <div className="grid grid-cols-12 gap-6 mt-6">
        <DocumentationPreview
          pipelineId={pipeline.id}
          pipelineName={stripDummy(pipeline.name)}
          documentation={pipeline.documentation}
          onSave={(doc) => updatePipeline({ documentation: doc })}
          isSaving={isSaving}
          canEdit={pipeline.can_edit}
        />

        {pipeline.topology_enabled && (
          <LineageTopology pipelineId={pipeline.id} fullWidth />
        )}

        <div className="col-span-12 lg:col-span-7">
          <SchemaViewer
            fields={pipeline.fields}
            pipelineId={pipeline.id}
            canEdit={pipeline.can_edit}
            schemaManuallyEdited={pipeline.schema_manually_edited}
            networkNames={networkNames}
          />
        </div>
        <div className="col-span-12 lg:col-span-5">
          <UsageCard etlName={pipeline.task_id ?? pipeline.name} />
        </div>

        <div className="col-span-12">
          <DataStructureCard
            pipelineId={pipeline.id}
            schedule={pipeline.schedule}
            canEdit={pipeline.can_edit}
          />
        </div>
      </div>
    </div>
  );
}
