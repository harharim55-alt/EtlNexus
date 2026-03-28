import { useState, useEffect, useCallback, useRef } from "react";
import {
  FileText,
  Edit3,
  Save,
  X,
  History,
} from "lucide-react";
import { RevisionHistoryPanel } from "./RevisionHistoryPanel";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkDirective from "remark-directive";
import remarkDirectiveRehype from "remark-directive-rehype";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import rehypeHighlight from "rehype-highlight";

import { markdownComponents } from "./documentation/markdown-components";
import { MarkdownEditor } from "./MarkdownEditor";

/** Allow safe HTML elements while blocking XSS vectors like <script>. */
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

/* ── Empty state ──────────────────────────────────────────────────── */

function EmptyDocState({ canEdit }: { canEdit: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <div className="size-12 rounded-xl bg-hover-bg border border-border flex items-center justify-center">
        <FileText className="size-5 text-text-faint" />
      </div>
      <div className="text-center">
        <p className="text-sm text-text-muted font-medium">
          No documentation yet
        </p>
        <p className="text-[11px] text-text-faint mt-1">
          {canEdit
            ? "Switch to Edit to start writing in Markdown"
            : "Only team members can add documentation"}
        </p>
      </div>
    </div>
  );
}

/* ── Component ─────────────────────────────────────────────────────── */

type ModalTab = "preview" | "edit" | "history";

interface DocumentationModalProps {
  open: boolean;
  onClose: () => void;
  pipelineId: string;
  pipelineName: string;
  documentation: string | null;
  onSave: (documentation: string) => void;
  isSaving: boolean;
  canEdit: boolean;
}

export function DocumentationModal({
  open,
  onClose,
  pipelineId,
  pipelineName,
  documentation,
  onSave,
  isSaving,
  canEdit,
}: DocumentationModalProps) {
  const [activeTab, setActiveTab] = useState<ModalTab>("preview");
  const [editValue, setEditValue] = useState(documentation ?? "");
  const [cheatsheetOpen, setCheatsheetOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isEditing = activeTab === "edit";

  const previewContent = editValue || documentation || "";

  useEffect(() => {
    setEditValue(documentation ?? "");
  }, [documentation]);

  useEffect(() => {
    if (open) {
      setActiveTab("preview");
      setEditValue(documentation ?? "");
      setCheatsheetOpen(false);
    }
  }, [open, documentation]);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isEditing]);

  // Escape to close + Ctrl+S to save
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "s" && (e.metaKey || e.ctrlKey) && isEditing) {
        e.preventDefault();
        onSave(editValue);
      }
    },
    [onClose, isEditing, editValue, onSave],
  );

  useEffect(() => {
    if (!open) return;
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, handleKeyDown]);

  const handleSave = () => {
    onSave(editValue);
    setActiveTab("preview");
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-5xl h-[85vh] bg-surface-modal border border-border rounded-2xl shadow-2xl shadow-black/50 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* ── Header ─────────────────────────────────────────────── */}
        <div className="px-7 py-4 border-b border-border bg-surface-raised flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            <div className="size-9 bg-indigo-500/10 border border-indigo-500/20 rounded-xl flex items-center justify-center">
              <FileText className="size-[18px] text-indigo-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-foreground tracking-tight">
                {pipelineName}
              </h2>
              <p className="text-[11px] text-text-muted font-mono mt-0.5">
                Documentation.md
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Segmented control: Preview / Edit / History */}
            <div className="flex bg-hover-bg rounded-lg p-0.5 border border-border">
              <button
                onClick={() => { setActiveTab("preview"); setCheatsheetOpen(false); }}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${
                  activeTab === "preview"
                    ? "bg-hover-bg-strong text-foreground shadow-sm"
                    : "text-text-muted hover:text-text-primary"
                }`}
              >
                <FileText className="size-3" />
                Preview
              </button>
              <button
                onClick={() => canEdit && setActiveTab("edit")}
                disabled={!canEdit}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${
                  !canEdit
                    ? "text-text-faint cursor-not-allowed opacity-40"
                    : activeTab === "edit"
                      ? "bg-hover-bg-strong text-foreground shadow-sm"
                      : "text-text-muted hover:text-text-primary"
                }`}
                title={!canEdit ? "You don't have permission to edit this pipeline's documentation" : undefined}
              >
                <Edit3 className="size-3" />
                Edit
              </button>
              <button
                onClick={() => { setActiveTab("history"); setCheatsheetOpen(false); }}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${
                  activeTab === "history"
                    ? "bg-hover-bg-strong text-foreground shadow-sm"
                    : "text-text-muted hover:text-text-primary"
                }`}
              >
                <History className="size-3" />
                History
              </button>
            </div>

            {/* Save (only in edit mode) */}
            {isEditing && canEdit && (
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-2 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-500/15 animate-in fade-in duration-150"
              >
                <Save className="size-3.5" />
                {isSaving ? "Saving\u2026" : "Save"}
              </button>
            )}

            <div className="w-px h-5 bg-hover-bg-strong mx-1" />

            <button
              onClick={onClose}
              className="p-2 text-text-muted hover:text-foreground hover:bg-hover-bg rounded-lg transition-all duration-200 border border-transparent hover:border-border"
            >
              <X className="size-[18px]" />
            </button>
          </div>
        </div>

        {/* ── Toolbar + Editor (edit mode) ─────────────────────── */}
        {isEditing && (
          <MarkdownEditor
            editValue={editValue}
            onEditValueChange={setEditValue}
            textareaRef={textareaRef}
            cheatsheetOpen={cheatsheetOpen}
            onToggleCheatsheet={() => setCheatsheetOpen((v) => !v)}
            onCloseCheatsheet={() => setCheatsheetOpen(false)}
          />
        )}

        {/* ── Body (non-edit modes) ───────────────────────────── */}
        {!isEditing && (
        <div className="flex-1 overflow-auto bg-background custom-scrollbar">
          {activeTab === "history" ? (
            <RevisionHistoryPanel
              pipelineId={pipelineId}
              field="documentation"
              canEdit={canEdit}
              onRestored={() => setActiveTab("preview")}
            />
          ) : (
            <div className="p-10 max-w-4xl mx-auto">
              {previewContent.trim() ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkDirective, remarkDirectiveRehype]}
                  rehypePlugins={[rehypeRaw, [rehypeSanitize, sanitizeSchema], rehypeHighlight]}
                  components={markdownComponents}
                >
                  {previewContent}
                </ReactMarkdown>
              ) : (
                <EmptyDocState canEdit={canEdit} />
              )}
            </div>
          )}
        </div>
        )}

        {/* ── Footer ─────────────────────────────────────────────── */}
        <div className="px-7 py-2.5 bg-surface-raised border-t border-border text-[11px] font-mono text-text-faint flex justify-between shrink-0">
          {activeTab === "edit" ? (
            <>
              <span>Markdown + GFM &middot; Use toolbar for formatting</span>
              <span>Ctrl+S to save &middot; Esc to close</span>
            </>
          ) : activeTab === "history" ? (
            <>
              <span>Revision history &middot; Previous versions of documentation</span>
              <span>Esc to close</span>
            </>
          ) : (
            <>
              <span>{canEdit ? "Read-only preview" : "View only — you don\u2019t have edit permissions"}</span>
              <span>Esc to close</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
