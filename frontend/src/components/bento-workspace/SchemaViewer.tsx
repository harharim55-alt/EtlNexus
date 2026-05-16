import { useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Box, Globe, Pencil, Plus, Save, Trash2, X } from "lucide-react";
import type { PipelineField } from "@/types/pipeline";
import apiClient from "@/api/client";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

interface SchemaViewerProps {
  fields: PipelineField[];
  pipelineId?: string;
  canEdit?: boolean;
  schemaManuallyEdited?: boolean;
  networkNames?: string[];
}

function getDisplayDataType(field: PipelineField): string {
  if (field.data_type) return field.data_type;
  const lower = field.name.toLowerCase();
  if (lower.includes("id")) return "UUID";
  if (lower.includes("amount") || lower.includes("price")) return "FLOAT8";
  if (lower.includes("date") || lower.includes("time") || lower.includes("created"))
    return "TIMESTAMP";
  if (lower.startsWith("is_") || lower.startsWith("has_")) return "BOOL";
  return "VARCHAR";
}

export function SchemaViewer({ fields, pipelineId, canEdit, schemaManuallyEdited, networkNames }: SchemaViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [editOpen, setEditOpen] = useState(false);

  const virtualizer = useVirtualizer({
    count: fields.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 40,
    overscan: 10,
  });

  return (
    <>
      <div className="bg-card border border-border rounded-2xl flex flex-col overflow-hidden max-h-[460px]">
        <div className="p-5 border-b border-border bg-card/50 backdrop-blur flex items-center justify-between">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-[11px] font-mono uppercase tracking-widest text-text-muted flex items-center gap-2">
              <Box className="w-3.5 h-3.5" /> Data Structure
            </h3>
            {schemaManuallyEdited && (
              <span className="text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                manual
              </span>
            )}
            {networkNames && networkNames.length > 0 && networkNames.map((name) => (
              <span
                key={name}
                className="text-[9px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1"
              >
                <Globe className="size-2.5" />
                {name}
              </span>
            ))}
          </div>
          {canEdit && pipelineId && (
            <button
              onClick={() => setEditOpen(true)}
              className="p-1.5 text-text-faint hover:text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-all cursor-pointer"
              title="Edit schema"
            >
              <Pencil className="size-3.5" />
            </button>
          )}
        </div>
        <div ref={scrollRef} className="overflow-y-auto p-2 custom-scrollbar">
          {fields.length === 0 ? (
            <div className="text-center text-text-faint text-xs py-6 font-mono">
              No fields defined
            </div>
          ) : (
            <div
              style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}
            >
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const field = fields[virtualRow.index];
                return (
                  <div
                    key={field.id}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      height: `${virtualRow.size}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                    className="flex justify-between items-center px-4 py-2.5 rounded-lg hover:bg-hover-bg transition-colors group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-1.5 h-1.5 rounded-full bg-slate-700 group-hover:bg-indigo-500 transition-colors" />
                      <span className="font-mono text-sm text-text-primary group-hover:text-foreground transition-colors">
                        {field.name}
                      </span>
                    </div>
                    <span className="text-[10px] text-text-muted font-mono bg-background px-2 py-1 rounded border border-border">
                      {getDisplayDataType(field)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {editOpen && pipelineId && (
        <SchemaEditorModal
          pipelineId={pipelineId}
          fields={fields}
          onClose={() => setEditOpen(false)}
        />
      )}
    </>
  );
}

/* ── Schema editor modal ────────────────────────────────────────────── */

function SchemaEditorModal({
  pipelineId,
  fields: initialFields,
  onClose,
}: {
  pipelineId: string;
  fields: PipelineField[];
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [rows, setRows] = useState(
    initialFields.map((f) => ({ name: f.name, data_type: f.data_type ?? "" }))
  );
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiClient.put(`/pipelines/${pipelineId}/fields`, {
        fields: rows
          .filter((r) => r.name.trim())
          .map((r, i) => ({
            id: crypto.randomUUID(),
            name: r.name,
            data_type: r.data_type || null,
            ordinal_position: i,
          })),
      });
      queryClient.invalidateQueries({ queryKey: ["pipeline", pipelineId] });
      toast.success("Schema updated");
      onClose();
    } catch {
      toast.error("Failed to update schema");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-in fade-in duration-150">
      <div className="bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl animate-in zoom-in-95 duration-200 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-border shrink-0">
          <h2 className="text-lg font-semibold text-foreground">Edit Schema</h2>
          <button onClick={onClose} className="p-1 text-text-muted hover:text-foreground cursor-pointer">
            <X className="size-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-2 custom-scrollbar">
          {rows.map((row, i) => (
            <div key={i} className="flex gap-2 items-center">
              <input
                value={row.name}
                onChange={(e) => {
                  const next = [...rows];
                  next[i] = { ...next[i], name: e.target.value };
                  setRows(next);
                }}
                placeholder="Field name"
                className="flex-1 bg-background border border-border-prominent rounded-lg px-3 py-1.5 text-sm text-foreground font-mono focus:outline-none focus:border-indigo-500/50"
              />
              <input
                value={row.data_type}
                onChange={(e) => {
                  const next = [...rows];
                  next[i] = { ...next[i], data_type: e.target.value };
                  setRows(next);
                }}
                placeholder="Type"
                className="w-28 bg-background border border-border-prominent rounded-lg px-3 py-1.5 text-sm text-foreground font-mono focus:outline-none focus:border-indigo-500/50"
              />
              <button
                onClick={() => setRows(rows.filter((_, j) => j !== i))}
                className="p-1 text-text-muted hover:text-rose-400 cursor-pointer"
              >
                <Trash2 className="size-3.5" />
              </button>
            </div>
          ))}
          <button
            onClick={() => setRows([...rows, { name: "", data_type: "" }])}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-mono cursor-pointer flex items-center gap-1 mt-2"
          >
            <Plus className="size-3" /> Add field
          </button>
        </div>

        <div className="flex justify-end gap-2 p-5 border-t border-border shrink-0">
          <button onClick={onClose} className="px-4 py-2 text-sm text-text-secondary hover:text-foreground rounded-lg">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5"
          >
            <Save className="size-3.5" />
            {saving ? "Saving..." : "Save Schema"}
          </button>
        </div>
      </div>
    </div>
  );
}
