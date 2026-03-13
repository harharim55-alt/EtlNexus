import { useState } from "react";
import { History, RotateCcw, User, RefreshCw, FileText } from "lucide-react";
import { useRevisions, useRestoreRevision } from "@/hooks/use-revisions";

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function SourceBadge({ source }: { source: string }) {
  const config = {
    user: { label: "User edit", bg: "bg-indigo-500/10", text: "text-indigo-400", border: "border-indigo-500/20" },
    restore: { label: "Restored", bg: "bg-amber-500/10", text: "text-amber-400", border: "border-amber-500/20" },
    system: { label: "System", bg: "bg-slate-500/10", text: "text-slate-400", border: "border-slate-500/20" },
  }[source] ?? { label: source, bg: "bg-slate-500/10", text: "text-slate-400", border: "border-slate-500/20" };

  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-md ${config.bg} ${config.text} border ${config.border}`}>
      {config.label}
    </span>
  );
}

interface RevisionHistoryPanelProps {
  pipelineId: string;
  field: "description" | "documentation";
  canEdit: boolean;
  onRestored?: () => void;
}

export function RevisionHistoryPanel({
  pipelineId,
  field,
  canEdit,
  onRestored,
}: RevisionHistoryPanelProps) {
  const { data, isLoading } = useRevisions(pipelineId, field);
  const { mutate: restore, isPending: isRestoring } = useRestoreRevision(pipelineId);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const handleRestore = (revisionId: string) => {
    restore(revisionId, {
      onSuccess: () => {
        setConfirmId(null);
        onRestored?.();
      },
    });
  };

  if (isLoading) {
    return (
      <div className="p-10 flex flex-col items-center justify-center gap-3">
        <div className="size-5 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
        <p className="text-xs text-slate-500">Loading revision history...</p>
      </div>
    );
  }

  const revisions = data?.items ?? [];

  if (revisions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <div className="size-12 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center">
          <History className="size-5 text-slate-600" />
        </div>
        <div className="text-center">
          <p className="text-sm text-slate-500 font-medium">No revision history</p>
          <p className="text-[11px] text-slate-600 mt-1">
            Changes will be tracked after the first edit
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-3">
      <div className="flex items-center gap-2 mb-6">
        <History className="size-4 text-slate-500" />
        <h3 className="text-sm font-medium text-slate-400">
          {revisions.length} revision{revisions.length !== 1 ? "s" : ""}
        </h3>
      </div>

      {revisions.map((rev) => (
        <div
          key={rev.id}
          className="bg-white/[0.02] border border-white/[0.06] rounded-xl overflow-hidden hover:border-white/[0.1] transition-colors"
        >
          {/* Revision header */}
          <div className="px-5 py-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex items-center gap-1.5 text-slate-400 shrink-0">
                <User className="size-3" />
                <span className="text-xs font-medium">{rev.changed_by}</span>
              </div>
              <SourceBadge source={rev.change_source} />
              <span className="text-[11px] text-slate-600 font-mono shrink-0">
                {formatRelativeTime(rev.created_at)}
              </span>
            </div>

            {canEdit && (
              <>
                {confirmId === rev.id ? (
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[11px] text-amber-400">Restore this version?</span>
                    <button
                      onClick={() => handleRestore(rev.id)}
                      disabled={isRestoring}
                      className="text-[11px] font-medium text-amber-400 hover:text-amber-300 px-2 py-1 bg-amber-500/10 border border-amber-500/20 rounded-md transition-colors disabled:opacity-50"
                    >
                      {isRestoring ? "Restoring..." : "Confirm"}
                    </button>
                    <button
                      onClick={() => setConfirmId(null)}
                      className="text-[11px] text-slate-500 hover:text-slate-300 px-2 py-1 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmId(rev.id)}
                    className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-indigo-400 px-2 py-1 hover:bg-indigo-500/10 rounded-md transition-all border border-transparent hover:border-indigo-500/20 shrink-0"
                  >
                    <RotateCcw className="size-3" />
                    Restore
                  </button>
                )}
              </>
            )}
          </div>

          {/* Content preview */}
          <div className="px-5 pb-4">
            {rev.content ? (
              <div className="bg-[#08080d] border border-white/[0.04] rounded-lg px-4 py-3 max-h-32 overflow-hidden relative">
                <pre className="text-xs font-mono text-slate-500 whitespace-pre-wrap break-words leading-relaxed">
                  {rev.content.length > 500 ? rev.content.slice(0, 500) + "..." : rev.content}
                </pre>
                {rev.content.length > 500 && (
                  <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-[#08080d] to-transparent" />
                )}
              </div>
            ) : (
              <p className="text-[11px] text-slate-600 italic px-1">Empty content</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Compact revision list for description history popover ───────── */

interface CompactRevisionListProps {
  pipelineId: string;
  canEdit: boolean;
  onRestored?: () => void;
}

export function CompactRevisionList({
  pipelineId,
  canEdit,
  onRestored,
}: CompactRevisionListProps) {
  const { data, isLoading } = useRevisions(pipelineId, "description");
  const { mutate: restore, isPending: isRestoring } = useRestoreRevision(pipelineId);

  if (isLoading) {
    return (
      <div className="p-4 flex items-center justify-center">
        <div className="size-4 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  const revisions = data?.items ?? [];

  if (revisions.length === 0) {
    return (
      <div className="px-4 py-5 text-center">
        <FileText className="size-4 text-slate-600 mx-auto mb-2" />
        <p className="text-[11px] text-slate-500">No description history yet</p>
      </div>
    );
  }

  return (
    <div className="max-h-64 overflow-y-auto custom-scrollbar">
      {revisions.slice(0, 10).map((rev) => (
        <div
          key={rev.id}
          className="px-4 py-2.5 border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] transition-colors"
        >
          <div className="flex items-center justify-between gap-2 mb-1">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-[10px] font-medium text-slate-400 truncate">
                {rev.changed_by}
              </span>
              <SourceBadge source={rev.change_source} />
            </div>
            <span className="text-[10px] text-slate-600 font-mono shrink-0">
              {formatRelativeTime(rev.created_at)}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 truncate mb-1.5">
            {rev.content || "(empty)"}
          </p>
          {canEdit && (
            <button
              onClick={() =>
                restore(rev.id, {
                  onSuccess: () => onRestored?.(),
                })
              }
              disabled={isRestoring}
              className="flex items-center gap-1 text-[10px] text-slate-600 hover:text-indigo-400 transition-colors disabled:opacity-50"
            >
              <RefreshCw className="size-2.5" />
              Restore
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
