import { usePipelineDetail } from "@/hooks/use-pipeline-detail";
import { useUpdatePipeline } from "@/hooks/use-update-pipeline";
import { useDataProductStore } from "@/stores/data-product-store";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { BentoHeader } from "@/components/bento-workspace/BentoHeader";
import { DocumentationPreview } from "@/components/bento-workspace/DocumentationPreview";
import { ConsumeSnippet } from "@/components/bento-workspace/ConsumeSnippet";
import { SchemaViewer } from "@/components/bento-workspace/SchemaViewer";
import { ProductTags } from "./ProductTags";
import { TagWorkspace } from "./TagWorkspace";
import { stripDummy } from "@/lib/format";

export function DataProductWorkspace() {
  const selectedProductId = useDataProductStore((s) => s.selectedProductId);
  const { data: pipeline, isLoading, error, refetch } = usePipelineDetail(selectedProductId);
  const { mutate: updatePipeline, isPending: isSaving } = useUpdatePipeline(selectedProductId ?? "");

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
          <Skeleton className="col-span-12 lg:col-span-7 h-64 bg-hover-bg rounded-2xl" />
          <Skeleton className="col-span-12 lg:col-span-5 h-64 bg-hover-bg rounded-2xl" />
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

  if (pipeline.is_tag) {
    return <TagWorkspace tag={pipeline} onSave={(body) => updatePipeline(body)} isSaving={isSaving} />;
  }

  return (
    <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
      <BentoHeader
        pipeline={pipeline}
        onSaveDescription={(description) => updatePipeline({ description })}
        isSaving={isSaving}
        canEdit={pipeline.can_edit}
      />

      <div className="grid grid-cols-12 gap-6 mt-6">
        {/* Documentation */}
        <DocumentationPreview
          pipelineId={pipeline.id}
          pipelineName={stripDummy(pipeline.name)}
          documentation={pipeline.documentation}
          onSave={(doc) => updatePipeline({ documentation: doc })}
          isSaving={isSaving}
          canEdit={pipeline.can_edit}
        />

        {/* Data structure (schema — auto-fetched from Spark Connect, manually editable) */}
        <div className="col-span-12 lg:col-span-7">
          <SchemaViewer
            fields={pipeline.fields}
            pipelineId={pipeline.id}
            canEdit={pipeline.can_edit}
            schemaManuallyEdited={pipeline.schema_manually_edited}
          />
        </div>

        {/* Import & consume (auto-generated, manually overridable) */}
        <div className="col-span-12 lg:col-span-5">
          <ConsumeSnippet
            defaultSnippet={pipeline.default_import_snippet}
            importSnippet={pipeline.import_snippet}
            canEdit={pipeline.can_edit}
            isSaving={isSaving}
            onSave={(snippet) => updatePipeline({ import_snippet: snippet })}
          />
        </div>

        {/* Tags */}
        <div className="col-span-12">
          <ProductTags productId={pipeline.id} tags={pipeline.tags} canEdit={pipeline.can_edit} />
        </div>
      </div>
    </div>
  );
}
