import { lazy, Suspense, useState } from "react";
import { FileText, Maximize2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkDirective from "remark-directive";
import remarkDirectiveRehype from "remark-directive-rehype";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import rehypeHighlight from "rehype-highlight";
import { markdownComponents } from "./documentation/markdown-components";

const DocumentationModal = lazy(() =>
  import("./DocumentationModal").then((m) => ({ default: m.DocumentationModal }))
);

const sanitizeSchema = {
  ...defaultSchema,
  tagNames: [
    ...(defaultSchema.tagNames ?? []),
    "details",
    "summary",
    "section",
  ],
  attributes: {
    ...defaultSchema.attributes,
    div: [...(defaultSchema.attributes?.div ?? []), "dir", "lang", "className"],
    section: [...(defaultSchema.attributes?.section ?? []), "className"],
    code: [...(defaultSchema.attributes?.code ?? []), "className"],
    span: [...(defaultSchema.attributes?.span ?? []), "className"],
    pre: [...(defaultSchema.attributes?.pre ?? []), "className"],
  },
};

interface DocumentationPreviewProps {
  pipelineId: string;
  pipelineName: string;
  documentation: string | null;
  onSave: (doc: string) => void;
  isSaving: boolean;
  canEdit: boolean;
}

export function DocumentationPreview({
  pipelineId,
  pipelineName,
  documentation,
  onSave,
  isSaving,
  canEdit,
}: DocumentationPreviewProps) {
  const [docOpen, setDocOpen] = useState(false);

  return (
    <>
      <div
        className="col-span-12 bg-card border border-border rounded-2xl p-5 cursor-pointer hover:border-border-prominent transition-colors group"
        onClick={() => setDocOpen(true)}
      >
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[11px] font-mono uppercase tracking-widest text-text-secondary flex items-center gap-2">
            <FileText className="w-3.5 h-3.5" /> Documentation
          </h3>
          <Maximize2 className="size-3.5 text-text-faint group-hover:text-indigo-400 transition-colors" />
        </div>
        {documentation?.trim() ? (
          <div className="relative max-h-32 overflow-hidden">
            <div className="text-sm leading-relaxed">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkDirective, remarkDirectiveRehype]}
                rehypePlugins={[rehypeRaw, [rehypeSanitize, sanitizeSchema], rehypeHighlight]}
                components={markdownComponents}
              >
                {documentation}
              </ReactMarkdown>
            </div>
            {/* Fade-out gradient at the bottom */}
            <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-card to-transparent pointer-events-none" />
          </div>
        ) : (
          <p className="text-sm text-text-faint italic">
            {canEdit ? "Click to add documentation" : "No documentation yet"}
          </p>
        )}
      </div>

      <Suspense fallback={null}>
        <DocumentationModal
          open={docOpen}
          onClose={() => setDocOpen(false)}
          pipelineId={pipelineId}
          pipelineName={pipelineName}
          documentation={documentation}
          onSave={(doc) => {
            onSave(doc);
            setDocOpen(false);
          }}
          isSaving={isSaving}
          canEdit={canEdit}
        />
      </Suspense>
    </>
  );
}
