import { lazy, Suspense, useState } from "react";
import { Clock, Users } from "lucide-react";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useSyncPipeline } from "@/hooks/use-sync-pipeline";
import { useTopology } from "@/hooks/use-topology";
import type { PipelineDetail } from "@/types/pipeline";
import { stripDummy, formatRelativeTime } from "@/lib/format";
import { HeaderActions } from "./HeaderActions";
import { EditableTitle } from "./EditableTitle";
import { RunSelector } from "./RunSelector";
import { AIRFLOW_URL } from "@/lib/config";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const DocumentationModal = lazy(() =>
  import("./DocumentationModal").then((m) => ({ default: m.DocumentationModal }))
);

interface BentoHeaderProps {
  pipeline: PipelineDetail;
  onSaveDescription: (description: string) => void;
  onSaveDocumentation: (documentation: string) => void;
  isSaving: boolean;
  canEdit: boolean;
}

export function BentoHeader({
  pipeline,
  onSaveDescription,
  onSaveDocumentation,
  isSaving,
  canEdit,
}: BentoHeaderProps) {
  const { mutate: sync, isPending: isSyncing } = useSyncPipeline(pipeline.id);
  const { data: topology } = useTopology(pipeline.id);

  const [docOpen, setDocOpen] = useState(false);

  return (
    <>
      <div className="bg-card border border-border rounded-2xl p-5">
        {/* Identity row: Name + Status + Category | Metadata + Docs + Sync */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-xl font-semibold text-foreground tracking-tight truncate">
              {stripDummy(pipeline.name)}
            </h1>
            <StatusBadge status={pipeline.airflow_status} size="md" />
            {pipeline.category && (
              <span className="text-[10px] font-mono uppercase tracking-[0.15em] text-indigo-400 bg-indigo-500/[0.08] px-2.5 py-1 rounded-md border border-indigo-500/15 shrink-0">
                {pipeline.category}
              </span>
            )}
            {pipeline.team && (
              <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-500/[0.08] px-2.5 py-1 rounded-md border border-emerald-500/15 shrink-0">
                <Users className="size-3" />
                {pipeline.team}
              </span>
            )}
            {pipeline.last_checked_at && (
              <Tooltip>
                <TooltipTrigger className="flex items-center gap-1 text-[10px] font-mono text-text-muted bg-hover-bg px-2 py-1 rounded-md border border-border shrink-0 cursor-default">
                  <Clock className="size-3" />
                  {formatRelativeTime(pipeline.last_checked_at)}
                </TooltipTrigger>
                <TooltipContent
                  side="bottom"
                  className="bg-card border-border-prominent text-foreground text-xs font-medium"
                >
                  Last synced from Airflow
                </TooltipContent>
              </Tooltip>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <RunSelector pipelineId={pipeline.id} />

            <div className="w-px h-5 bg-hover-bg-strong" />

            <HeaderActions
              lastUpdatedBy={pipeline.last_updated_by}
              lastUpdatedAt={pipeline.last_updated_at}
              executionDate={pipeline.execution_date}
              dagId={topology?.dag_ids?.[0] ?? null}
              taskId={pipeline.task_id}
              airflowUrl={AIRFLOW_URL}
              isSyncing={isSyncing}
              onSync={() => sync()}
              onOpenDocs={() => setDocOpen(true)}
            />
          </div>
        </div>

        {/* Editable description */}
        <EditableTitle
          pipelineId={pipeline.id}
          description={pipeline.description}
          canEdit={canEdit}
          isSaving={isSaving}
          onSaveDescription={onSaveDescription}
        />
      </div>

      <Suspense fallback={null}>
        <DocumentationModal
          open={docOpen}
          onClose={() => setDocOpen(false)}
          pipelineId={pipeline.id}
          pipelineName={stripDummy(pipeline.name)}
          documentation={pipeline.documentation}
          onSave={(doc) => {
            onSaveDocumentation(doc);
            setDocOpen(false);
          }}
          isSaving={isSaving}
          canEdit={canEdit}
        />
      </Suspense>
    </>
  );
}
