import { useState, useEffect, useRef } from "react";
import { Edit3, Save, History, X } from "lucide-react";
import { CompactRevisionList } from "./RevisionHistoryPanel";

/* ── Props ─────────────────────────────────────────────────────────── */

interface EditableTitleProps {
  pipelineId: string;
  description: string | null;
  canEdit: boolean;
  isSaving: boolean;
  onSaveDescription: (description: string) => void;
}

/* ── Component ─────────────────────────────────────────────────────── */

export function EditableTitle({
  pipelineId,
  description,
  canEdit,
  isSaving,
  onSaveDescription,
}: EditableTitleProps) {
  const [isEditingDesc, setIsEditingDesc] = useState(false);
  const [editValue, setEditValue] = useState(description ?? "");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [descHistoryOpen, setDescHistoryOpen] = useState(false);
  const descHistoryRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setEditValue(description ?? "");
    setIsEditingDesc(false);
    setDescHistoryOpen(false);
  }, [pipelineId, description]);

  // Close description history popover on outside click
  useEffect(() => {
    if (!descHistoryOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (descHistoryRef.current && !descHistoryRef.current.contains(e.target as Node)) {
        setDescHistoryOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [descHistoryOpen]);

  useEffect(() => {
    if (isEditingDesc && textareaRef.current) {
      const el = textareaRef.current;
      el.focus();
      el.selectionStart = el.value.length;
    }
  }, [isEditingDesc]);

  const handleSaveDesc = () => {
    onSaveDescription(editValue);
    setIsEditingDesc(false);
  };

  const handleCancelEdit = () => {
    setEditValue(description ?? "");
    setIsEditingDesc(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSaveDesc();
    }
    if (e.key === "Escape") {
      handleCancelEdit();
    }
  };

  if (isEditingDesc && canEdit) {
    return (
      <div className="mt-3 animate-in fade-in duration-200">
        <textarea
          ref={textareaRef}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={handleKeyDown}
          className="w-full bg-[#09090b] border border-indigo-500/40 rounded-xl p-4 text-sm text-slate-300 leading-relaxed focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition-all resize-none placeholder:text-slate-600"
          rows={3}
          placeholder="Enter a brief description of this pipeline..."
        />
        <div className="flex items-center justify-between mt-2">
          <span className="text-[10px] text-slate-600 font-mono select-none">
            Ctrl+Enter to save · Esc to cancel
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleCancelEdit}
              className="px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors rounded-lg"
            >
              Cancel
            </button>
            <button
              onClick={handleSaveDesc}
              disabled={isSaving}
              className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5"
            >
              <Save className="size-3" />
              {isSaving ? "Saving\u2026" : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-3 group/desc relative">
      <p className="text-slate-400 text-sm leading-relaxed max-w-3xl pr-10">
        {description || (
          <span className="text-slate-600 italic">No description</span>
        )}
      </p>
      <div className="absolute top-0 right-0 flex items-center gap-0.5 opacity-0 group-hover/desc:opacity-100 transition-all duration-200">
        {/* Description history */}
        <div className="relative" ref={descHistoryRef}>
          <button
            onClick={() => setDescHistoryOpen((v) => !v)}
            className="p-1.5 text-slate-600 hover:text-indigo-400 hover:bg-indigo-500/10 rounded-lg border border-transparent hover:border-indigo-500/20 transition-all duration-200"
            title="Description history"
          >
            <History className="size-3.5" />
          </button>
          {descHistoryOpen && (
            <div className="absolute top-full right-0 mt-1 z-50 w-80 bg-[#111116] border border-white/[0.08] rounded-xl shadow-2xl shadow-black/50 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="px-4 py-2.5 border-b border-white/[0.06] flex items-center justify-between">
                <span className="text-[11px] font-semibold text-white tracking-tight">Description History</span>
                <button onClick={() => setDescHistoryOpen(false)} className="p-0.5 text-slate-500 hover:text-white transition-colors rounded">
                  <X className="size-3" />
                </button>
              </div>
              <CompactRevisionList
                pipelineId={pipelineId}
                canEdit={canEdit}
                onRestored={() => setDescHistoryOpen(false)}
              />
            </div>
          )}
        </div>
        {/* Edit description */}
        {canEdit && (
          <button
            onClick={() => {
              setEditValue(description ?? "");
              setIsEditingDesc(true);
            }}
            className="p-1.5 text-slate-600 hover:text-indigo-400 hover:bg-indigo-500/10 rounded-lg border border-transparent hover:border-indigo-500/20 transition-all duration-200"
            title="Edit Description"
          >
            <Edit3 className="size-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}
