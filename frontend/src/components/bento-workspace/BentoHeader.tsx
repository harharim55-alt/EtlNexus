import { lazy, Suspense, useState } from "react";
import { Users, Clock } from "lucide-react";
import { useSyncPipeline } from "@/hooks/use-sync-pipeline";
import { useTopology } from "@/hooks/use-topology";
import type { PipelineDetail } from "@/types/pipeline";
import { stripDummy } from "@/lib/format";
import { HeaderActions } from "./HeaderActions";
import { EditableTitle } from "./EditableTitle";
import { RunSelector } from "./RunSelector";
import { PipelineSettingsModal } from "./PipelineSettingsModal";
import { AIRFLOW_URL } from "@/lib/config";

const DocumentationModal = lazy(() =>
  import("./DocumentationModal").then((m) => ({ default: m.DocumentationModal }))
);

interface BentoHeaderProps {
  pipeline: PipelineDetail;
  onSaveDescription: (description: string) => void;
  onSaveDocumentation: (documentation: string) => void;
  onUpdate: (updates: Record<string, unknown>) => void;
  isSaving: boolean;
  canEdit: boolean;
}

export function BentoHeader({
  pipeline,
  onSaveDescription,
  onSaveDocumentation,
  onUpdate,
  isSaving,
  canEdit,
}: BentoHeaderProps) {
  const { mutate: sync, isPending: isSyncing } = useSyncPipeline(pipeline.id);
  const { data: topology } = useTopology(pipeline.id);
  const [docOpen, setDocOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const tags = pipeline.tags ?? [];

  return (
    <>
      <div className="bg-card border border-border rounded-2xl p-5">
        {/* Identity row */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-xl font-semibold text-foreground tracking-tight truncate">
              {stripDummy(pipeline.name)}
            </h1>
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
            {(pipeline.schedule || pipeline.schedule_type) && (
              <span className="flex items-center gap-1 text-[10px] font-mono text-text-muted bg-hover-bg px-2.5 py-1 rounded-md border border-border shrink-0">
                <Clock className="size-3" />
                {pipeline.schedule ?? pipeline.schedule_type}
              </span>
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
              onOpenSettings={() => setSettingsOpen(true)}
              canEdit={canEdit}
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

        {/* Tags (read-only display) */}
        {tags.length > 0 && (
          <div className="mt-3 flex items-center gap-2 flex-wrap">
            {tags.map((tag) => (
              <span
                key={tag.id}
                className="text-[10px] font-mono px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20"
              >
                {tag.name}
              </span>
            ))}
          </div>
        )}

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

      <PipelineSettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        pipeline={pipeline}
        onUpdate={onUpdate}
        isSaving={isSaving}
      />
    </>
  );
}
