import { Users, Clock } from "lucide-react";
import type { PipelineDetail } from "@/types/pipeline";
import { stripDummy } from "@/lib/format";
import { EditableTitle } from "./EditableTitle";

interface BentoHeaderProps {
  pipeline: PipelineDetail;
  onSaveDescription: (description: string) => void;
  isSaving: boolean;
  canEdit: boolean;
}

/** Title card: product name + team + schedule, with an editable description. */
export function BentoHeader({
  pipeline,
  onSaveDescription,
  isSaving,
  canEdit,
}: BentoHeaderProps) {
  return (
    <div className="bg-card border border-border rounded-2xl p-5">
      {/* Identity row */}
      <div className="flex items-center gap-3 min-w-0 flex-wrap">
        <h1 className="text-xl font-semibold text-foreground tracking-tight truncate">
          {stripDummy(pipeline.name)}
        </h1>
        {pipeline.team && (
          <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-500/[0.08] px-2.5 py-1 rounded-md border border-emerald-500/15 shrink-0">
            <Users className="size-3" />
            {pipeline.team}
          </span>
        )}
        {pipeline.schedule_type && (
          <span className="flex items-center gap-1 text-[10px] font-mono text-text-muted bg-hover-bg px-2.5 py-1 rounded-md border border-border shrink-0">
            <Clock className="size-3" />
            {pipeline.schedule_type}
          </span>
        )}
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
  );
}
