import { useEffect, useState } from "react";
import { Layers } from "lucide-react";
import type { PipelineDetail } from "@/types/pipeline";
import { useTagMembers } from "@/hooks/use-tags";
import { usePipelineDetail } from "@/hooks/use-pipeline-detail";
import { Skeleton } from "@/components/ui/skeleton";
import { BentoHeader } from "@/components/bento-workspace/BentoHeader";
import { DocumentationPreview } from "@/components/bento-workspace/DocumentationPreview";
import { ConsumeSnippet } from "@/components/bento-workspace/ConsumeSnippet";
import { SchemaViewer } from "@/components/bento-workspace/SchemaViewer";
import { stripDummy } from "@/lib/format";

interface TagWorkspaceProps {
  tag: PipelineDetail;
  onSave: (body: { documentation?: string; import_snippet?: string | null }) => void;
  isSaving: boolean;
}

const noop = () => {};

/** A read-only view of a tagged sub-product (one tab of the tag page). */
function MemberPanel({ memberId }: { memberId: string }) {
  const { data: member, isLoading } = usePipelineDetail(memberId);

  if (isLoading || !member) {
    return (
      <div className="grid grid-cols-12 gap-6">
        <Skeleton className="col-span-12 h-24 bg-hover-bg rounded-2xl" />
        <Skeleton className="col-span-12 lg:col-span-7 h-64 bg-hover-bg rounded-2xl" />
        <Skeleton className="col-span-12 lg:col-span-5 h-64 bg-hover-bg rounded-2xl" />
      </div>
    );
  }

  return (
    <div>
      <BentoHeader pipeline={member} onSaveDescription={noop} isSaving={false} canEdit={false} />
      <div className="grid grid-cols-12 gap-6 mt-6">
        <DocumentationPreview
          pipelineId={member.id}
          pipelineName={stripDummy(member.name)}
          documentation={member.documentation}
          onSave={noop}
          isSaving={false}
          canEdit={false}
        />
        <div className="col-span-12 lg:col-span-7">
          <SchemaViewer
            fields={member.fields}
            pipelineId={member.id}
            canEdit={false}
            schemaManuallyEdited={member.schema_manually_edited}
          />
        </div>
        <div className="col-span-12 lg:col-span-5">
          <ConsumeSnippet
            pipelineName={member.name}
            team={member.team}
            importSnippet={member.import_snippet}
            isTag={member.is_tag}
            canEdit={false}
          />
        </div>
      </div>
    </div>
  );
}

/** Tag detail page: the tag's own info (no schema) + a tab per tagged sub-product. */
export function TagWorkspace({ tag, onSave, isSaving }: TagWorkspaceProps) {
  const { data: members, isLoading } = useTagMembers(tag.id);
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    if (members && members.length > 0) {
      setActiveId((cur) => (cur && members.some((m) => m.id === cur) ? cur : members[0].id));
    } else {
      setActiveId(null);
    }
  }, [members]);

  return (
    <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
      <BentoHeader
        pipeline={tag}
        onSaveDescription={noop}
        isSaving={isSaving}
        canEdit={false}
      />

      <div className="grid grid-cols-12 gap-6 mt-6">
        <DocumentationPreview
          pipelineId={tag.id}
          pipelineName={stripDummy(tag.name)}
          documentation={tag.documentation}
          onSave={(doc) => onSave({ documentation: doc })}
          isSaving={isSaving}
          canEdit={tag.can_edit}
        />
        <div className="col-span-12">
          <ConsumeSnippet
            pipelineName={tag.name}
            team={tag.team}
            importSnippet={tag.import_snippet}
            isTag
            canEdit={tag.can_edit}
            isSaving={isSaving}
            onSave={(snippet) => onSave({ import_snippet: snippet })}
          />
        </div>
      </div>

      {/* Tagged sub-products */}
      <div className="mt-8">
        <h2 className="text-[11px] font-mono uppercase tracking-widest text-text-muted flex items-center gap-2 mb-3">
          <Layers className="w-3.5 h-3.5" /> Tagged Products
        </h2>

        {isLoading ? (
          <Skeleton className="h-9 w-72 bg-hover-bg rounded-lg" />
        ) : !members || members.length === 0 ? (
          <p className="text-sm text-text-faint font-mono">
            No products tagged yet. Open a data product and apply this tag.
          </p>
        ) : (
          <>
            <div className="flex items-center gap-1 flex-wrap border-b border-border mb-6">
              {members.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setActiveId(m.id)}
                  className={`px-3 py-2 text-sm font-medium -mb-px border-b-2 transition-colors cursor-pointer ${
                    activeId === m.id
                      ? "border-indigo-500 text-indigo-400"
                      : "border-transparent text-text-muted hover:text-text-primary"
                  }`}
                >
                  {stripDummy(m.name)}
                </button>
              ))}
            </div>
            {activeId && <MemberPanel key={activeId} memberId={activeId} />}
          </>
        )}
      </div>
    </div>
  );
}
