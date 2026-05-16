import { useState } from "react";
import { Database, Plus, Trash2, Pencil } from "lucide-react";
import { usePipelineLogs, useCreatePipelineLog, useUpdatePipelineLog, useDeletePipelineLog } from "@/hooks/use-pipeline-logs";
import { Skeleton } from "@/components/ui/skeleton";
import type { PipelineLog } from "@/types/pipeline";
import { LogEditorModal } from "./LogEditorModal";

interface DataStructureCardProps {
  pipelineId: string;
  schedule: string | null;
  canEdit: boolean;
}

export function DataStructureCard({ pipelineId, schedule, canEdit }: DataStructureCardProps) {
  const { data, isLoading } = usePipelineLogs(pipelineId);
  const createLog = useCreatePipelineLog(pipelineId);
  const updateLog = useUpdatePipelineLog(pipelineId);
  const deleteLog = useDeletePipelineLog(pipelineId);
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorLogId, setEditorLogId] = useState<string | null>(null);
  const [editingLogId, setEditingLogId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");

  const logs = data?.items ?? [];
  const selectedLog = logs.find((l) => l.id === selectedLogId) ?? logs[0] ?? null;

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-2xl p-5">
        <Skeleton className="h-6 w-40 bg-hover-bg mb-4" />
        <Skeleton className="h-32 bg-hover-bg rounded-lg" />
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="bg-card border border-border rounded-2xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[11px] font-mono uppercase tracking-widest text-text-secondary flex items-center gap-2">
            <Database className="w-3.5 h-3.5" /> Data Structure
          </h3>
          {canEdit && (
            <button
              onClick={() => createLog.mutate({ name: "New Log" })}
              className="text-[10px] font-mono text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer flex items-center gap-1"
            >
              <Plus className="size-3" /> Add Log
            </button>
          )}
        </div>
        <p className="text-sm text-text-faint italic">No logs defined. Add a log to define data structure.</p>
      </div>
    );
  }

  return (
    <>
      <div className="bg-card border border-border rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-[11px] font-mono uppercase tracking-widest text-text-secondary flex items-center gap-2">
            <Database className="w-3.5 h-3.5" /> Data Structure
          </h3>
          <div className="flex items-center gap-3">
            {schedule && (
              <span className="text-[10px] font-mono text-text-muted">
                Schedule: <span className="text-foreground">{schedule}</span>
              </span>
            )}
            {canEdit && (
              <button
                onClick={() => createLog.mutate({ name: `Log ${logs.length + 1}` })}
                className="text-[10px] font-mono text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer flex items-center gap-1"
              >
                <Plus className="size-3" /> Add Log
              </button>
            )}
          </div>
        </div>

        <div className="flex gap-4">
          {/* Log list (left) */}
          <div className="w-48 shrink-0 space-y-1">
            {logs.map((log) => (
              <button
                key={log.id}
                onClick={() => setSelectedLogId(log.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm font-mono transition-all cursor-pointer flex items-center justify-between group ${
                  (selectedLog?.id === log.id)
                    ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                    : "text-text-secondary hover:bg-hover-bg border border-transparent"
                }`}
              >
                {editingLogId === log.id ? (
                  <input
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && editingName.trim()) {
                        updateLog.mutate({ logId: log.id, body: { name: editingName.trim() } });
                        setEditingLogId(null);
                      } else if (e.key === "Escape") {
                        setEditingLogId(null);
                      }
                    }}
                    onBlur={() => {
                      if (editingName.trim() && editingName.trim() !== log.name) {
                        updateLog.mutate({ logId: log.id, body: { name: editingName.trim() } });
                      }
                      setEditingLogId(null);
                    }}
                    onClick={(e) => e.stopPropagation()}
                    autoFocus
                    className="w-full bg-background border border-indigo-500/50 rounded px-1.5 py-0.5 text-sm font-mono text-foreground focus:outline-none"
                  />
                ) : (
                  <span className="truncate">{log.name}</span>
                )}
                {canEdit && editingLogId !== log.id && (
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingLogId(log.id);
                        setEditingName(log.name);
                      }}
                      className="text-text-muted hover:text-amber-400 transition-colors"
                      title="Rename log"
                    >
                      <Pencil className="size-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditorLogId(log.id);
                        setEditorOpen(true);
                      }}
                      className="text-text-muted hover:text-indigo-400 transition-colors"
                      title="Edit log"
                    >
                      <Database className="size-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteLog.mutate(log.id);
                      }}
                      className="text-text-muted hover:text-rose-400 transition-colors"
                      title="Delete log"
                    >
                      <Trash2 className="size-3" />
                    </button>
                  </div>
                )}
              </button>
            ))}
          </div>

          {/* Log detail (right) */}
          {selectedLog && <LogDetail log={selectedLog} />}
        </div>
      </div>

      {editorOpen && editorLogId && (
        <LogEditorModal
          open={editorOpen}
          onClose={() => setEditorOpen(false)}
          pipelineId={pipelineId}
          logId={editorLogId}
          logName={logs.find((l) => l.id === editorLogId)?.name ?? ""}
        />
      )}
    </>
  );
}

function LogDetail({ log }: { log: PipelineLog }) {
  const [selectedNetworkId, setSelectedNetworkId] = useState<string | null>(null);

  const selectedNetwork = log.networks.find((n) => n.network_id === selectedNetworkId);

  return (
    <div className="flex-1 min-w-0">
      {/* Networks */}
      {log.networks.length > 0 && (
        <div className="mb-4">
          <span className="text-[10px] font-mono uppercase tracking-widest text-text-faint block mb-2">
            Networks
          </span>
          <div className="flex gap-1.5 flex-wrap">
            {log.networks.map((ln) => (
              <button
                key={ln.network_id}
                onClick={() => setSelectedNetworkId(
                  selectedNetworkId === ln.network_id ? null : ln.network_id
                )}
                className={`text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer ${
                  selectedNetworkId === ln.network_id
                    ? "text-teal-300 bg-teal-500/15 border-teal-500/30"
                    : "text-text-muted bg-hover-bg border-border hover:border-border-prominent"
                }`}
              >
                {ln.network_name ?? ln.network_id}
              </button>
            ))}
          </div>
          {selectedNetwork?.retention && (
            <div className="mt-2 text-[10px] font-mono text-text-muted">
              Retention: <span className="text-foreground">{selectedNetwork.retention}</span>
            </div>
          )}
        </div>
      )}

      {/* Schema fields */}
      <div>
        <span className="text-[10px] font-mono uppercase tracking-widest text-text-faint block mb-2">
          Schema ({log.fields.length} fields)
        </span>
        {log.fields.length > 0 ? (
          <div className="space-y-1 max-h-60 overflow-y-auto custom-scrollbar">
            {log.fields.map((field) => (
              <div
                key={field.id}
                className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-hover-bg/50"
              >
                <span className="text-xs font-mono text-foreground">{field.name}</span>
                <span className="text-[10px] font-mono text-text-muted px-2 py-0.5 rounded bg-background border border-border">
                  {field.data_type ?? "VARCHAR"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-faint italic">No fields defined</p>
        )}
      </div>
    </div>
  );
}
