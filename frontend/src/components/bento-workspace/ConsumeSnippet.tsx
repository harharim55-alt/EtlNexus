import { useState } from "react";
import { Code, Pencil, RotateCcw } from "lucide-react";
import { CopyButton } from "@/components/shared/CopyButton";
import { stripDummy } from "@/lib/format";

interface ConsumeSnippetProps {
  pipelineName: string;
  team?: string | null;
  importSnippet?: string | null;
  canEdit?: boolean;
  isSaving?: boolean;
  /** Persist a manual override (string) or clear it to fall back to auto (null). */
  onSave?: (snippet: string | null) => void;
}

/** Build the auto-generated catalog consume snippet from the product name + team. */
function buildAutoSnippet(pipelineName: string, team?: string | null): string {
  const importName = stripDummy(pipelineName).toLowerCase().replace(/ /g, "_");
  const ns = team?.toLowerCase() ?? "dagger";
  return `from etls import Catalog, Engine\n\nCatalog(Engine.Spark).iceberg.${ns}.${importName}("date").consume().as_pyspark()`;
}

export function ConsumeSnippet({
  pipelineName,
  team,
  importSnippet,
  canEdit = false,
  isSaving = false,
  onSave,
}: ConsumeSnippetProps) {
  const isManual = !!importSnippet;
  const autoSnippet = buildAutoSnippet(pipelineName, team);
  const snippet = importSnippet || autoSnippet;

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(snippet);

  const startEdit = () => {
    setDraft(snippet);
    setEditing(true);
  };

  return (
    <div className="bg-card border border-border rounded-2xl p-5 shrink-0">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-[11px] font-mono uppercase tracking-widest text-text-muted flex items-center gap-2">
          <Code className="w-3.5 h-3.5" /> Import & Consume
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-hover-bg border border-border text-text-faint">
            {isManual ? "manual" : "auto"}
          </span>
        </h3>
        <div className="flex items-center gap-2">
          {canEdit && onSave && !editing && (
            <>
              <button
                onClick={startEdit}
                className="text-text-muted hover:text-indigo-400 transition-colors"
                title="Edit consume snippet (switch to manual)"
              >
                <Pencil className="size-3.5" />
              </button>
              {isManual && (
                <button
                  onClick={() => onSave(null)}
                  disabled={isSaving}
                  className="text-text-muted hover:text-amber-400 transition-colors"
                  title="Reset to auto-generated"
                >
                  <RotateCcw className="size-3.5" />
                </button>
              )}
            </>
          )}
          {!editing && <CopyButton text={snippet} />}
        </div>
      </div>

      {editing ? (
        <div className="space-y-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={5}
            className="w-full bg-background border border-border-prominent rounded-xl p-3 text-xs font-mono text-text-primary focus:outline-none focus:border-indigo-500/50"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setEditing(false)}
              className="px-3 py-1.5 text-xs text-text-secondary hover:text-foreground transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => { onSave?.(draft); setEditing(false); }}
              disabled={isSaving}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors"
            >
              Save
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-background rounded-xl p-4 border border-border overflow-x-auto">
          <pre className="text-xs font-mono leading-relaxed text-text-primary whitespace-pre-wrap">{snippet}</pre>
        </div>
      )}
    </div>
  );
}
