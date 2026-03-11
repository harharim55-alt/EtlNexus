import { useState, useEffect, useRef } from "react";
import {
  Edit3,
  Save,
  FileText,
  User,
  Calendar,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useSyncPipeline } from "@/hooks/use-sync-pipeline";
import type { PipelineDetail } from "@/types/pipeline";
import { DocumentationModal } from "./DocumentationModal";

interface BentoHeaderProps {
  pipeline: PipelineDetail;
  onSaveDescription: (description: string) => void;
  onSaveDocumentation: (documentation: string) => void;
  isSaving: boolean;
}

function formatDate(iso: string | null): string {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function BentoHeader({
  pipeline,
  onSaveDescription,
  onSaveDocumentation,
  isSaving,
}: BentoHeaderProps) {
  const { mutate: sync, isPending: isSyncing } = useSyncPipeline(pipeline.id);

  const [isEditingDesc, setIsEditingDesc] = useState(false);
  const [editValue, setEditValue] = useState(pipeline.description ?? "");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [docOpen, setDocOpen] = useState(false);

  useEffect(() => {
    setEditValue(pipeline.description ?? "");
    setIsEditingDesc(false);
  }, [pipeline.id, pipeline.description]);

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
    setEditValue(pipeline.description ?? "");
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

  return (
    <>
      <div className="bg-[#18181b] border border-white/5 rounded-2xl p-5">
        {/* ── Identity row: Name + Status + Category | Metadata + Docs + Sync */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-xl font-semibold text-white tracking-tight truncate">
              {pipeline.name}
            </h1>
            <StatusBadge status={pipeline.airflow_status} size="md" />
            {pipeline.category && (
              <span className="text-[10px] font-mono uppercase tracking-[0.15em] text-indigo-400 bg-indigo-500/[0.08] px-2.5 py-1 rounded-md border border-indigo-500/15 shrink-0">
                {pipeline.category}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {pipeline.last_updated_by && (
              <span
                className="hidden xl:flex items-center gap-1.5 text-[11px] text-slate-500 font-mono bg-white/[0.02] px-2.5 py-1.5 rounded-lg border border-white/5"
                title="Last updated by"
              >
                <User className="size-3 text-slate-600" />
                {pipeline.last_updated_by}
              </span>
            )}
            {pipeline.last_updated_at && (
              <span
                className="hidden xl:flex items-center gap-1.5 text-[11px] text-slate-500 font-mono bg-white/[0.02] px-2.5 py-1.5 rounded-lg border border-white/5"
                title="Last updated"
              >
                <Calendar className="size-3 text-slate-600" />
                {formatDate(pipeline.last_updated_at)}
              </span>
            )}

            {/* Docs icon-button */}
            <Tooltip>
              <TooltipTrigger
                render={
                  <Button
                    variant="outline"
                    size="icon-sm"
                    onClick={() => setDocOpen(true)}
                    className="border-white/10 bg-white/[0.03] text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 hover:border-indigo-500/20 transition-all duration-200"
                  />
                }
              >
                <FileText className="size-3.5" />
              </TooltipTrigger>
              <TooltipContent side="bottom">
                Open Documentation
              </TooltipContent>
            </Tooltip>

            {/* Sync button */}
            <Tooltip>
              <TooltipTrigger
                render={
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={isSyncing}
                    onClick={() => sync()}
                    className="border-white/10 bg-white/[0.03] text-slate-400 hover:text-white hover:bg-white/[0.07] transition-all duration-200"
                  />
                }
              >
                <RefreshCw
                  className={`size-3.5 ${isSyncing ? "animate-spin" : ""}`}
                />
                <span className="text-xs">
                  {isSyncing ? "Syncing\u2026" : "Sync"}
                </span>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                Refresh this pipeline from Airflow
              </TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* ── Editable description ───────────────────────────────── */}
        <div className="mt-3">
          {isEditingDesc ? (
            <div className="animate-in fade-in duration-200">
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
          ) : (
            <div className="group/desc relative">
              <p className="text-slate-400 text-sm leading-relaxed max-w-3xl pr-10">
                {pipeline.description || (
                  <span className="text-slate-600 italic">No description</span>
                )}
              </p>
              <button
                onClick={() => {
                  setEditValue(pipeline.description ?? "");
                  setIsEditingDesc(true);
                }}
                className="absolute top-0 right-0 p-1.5 text-slate-600 hover:text-indigo-400 opacity-0 group-hover/desc:opacity-100 transition-all duration-200 hover:bg-indigo-500/10 rounded-lg border border-transparent hover:border-indigo-500/20"
                title="Edit Description"
              >
                <Edit3 className="size-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      <DocumentationModal
        open={docOpen}
        onClose={() => setDocOpen(false)}
        pipelineName={pipeline.name}
        documentation={pipeline.documentation}
        onSave={(doc) => {
          onSaveDocumentation(doc);
          setDocOpen(false);
        }}
        isSaving={isSaving}
      />
    </>
  );
}
