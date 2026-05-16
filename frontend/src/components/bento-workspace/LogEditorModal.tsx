import { useState, useEffect } from "react";
import { X, Plus, Trash2 } from "lucide-react";
import { usePipelineLogs, useSetLogNetworks, useSetLogFields } from "@/hooks/use-pipeline-logs";
import { useNetworks, useCreateNetwork } from "@/hooks/use-networks";
import { useAuthStore } from "@/stores/auth-store";

interface LogEditorModalProps {
  open: boolean;
  onClose: () => void;
  pipelineId: string;
  logId: string;
  logName: string;
}

interface EditField {
  name: string;
  data_type: string;
}

interface EditNetwork {
  network_id: string;
  network_name: string;
  retention: string;
  selected: boolean;
}

export function LogEditorModal({ open, onClose, pipelineId, logId, logName }: LogEditorModalProps) {
  const { data: logsData } = usePipelineLogs(pipelineId);
  const { data: networksData } = useNetworks();
  const setNetworks = useSetLogNetworks(pipelineId, logId);
  const setFields = useSetLogFields(pipelineId, logId);
  const createNet = useCreateNetwork();
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === "admin";

  const log = logsData?.items.find((l) => l.id === logId);

  const [fields, setFieldsState] = useState<EditField[]>([]);
  const [editNetworks, setEditNetworks] = useState<EditNetwork[]>([]);
  const [activeTab, setActiveTab] = useState<"fields" | "networks">("fields");
  const [newNetworkName, setNewNetworkName] = useState("");

  useEffect(() => {
    if (log) {
      setFieldsState(log.fields.map((f) => ({ name: f.name, data_type: f.data_type ?? "" })));
      const allNetworks = networksData?.items ?? [];
      const logNetworkIds = new Set(log.networks.map((n) => n.network_id));
      setEditNetworks(
        allNetworks.map((n) => {
          const existing = log.networks.find((ln) => ln.network_id === n.id);
          return {
            network_id: n.id,
            network_name: n.name,
            retention: existing?.retention ?? "",
            selected: logNetworkIds.has(n.id),
          };
        })
      );
    }
  }, [log, networksData]);

  if (!open) return null;

  const handleSave = async () => {
    if (activeTab === "fields") {
      setFields.mutate(
        fields.filter((f) => f.name.trim()).map((f, i) => ({
          name: f.name,
          data_type: f.data_type || undefined,
          ordinal_position: i,
        })),
        { onSuccess: () => onClose() },
      );
    } else {
      const selectedNetworks = editNetworks
        .filter((n) => n.selected)
        .map((n) => ({
          network_id: n.network_id,
          retention: n.retention || undefined,
        }));
      setNetworks.mutate(selectedNetworks, { onSuccess: () => onClose() });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-in fade-in duration-150">
      <div className="bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl animate-in zoom-in-95 duration-200 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-border shrink-0">
          <h2 className="text-lg font-semibold text-foreground">
            Edit Log: {logName}
          </h2>
          <button onClick={onClose} className="p-1 text-text-muted hover:text-foreground transition-colors cursor-pointer">
            <X className="size-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border shrink-0">
          <button
            onClick={() => setActiveTab("fields")}
            className={`px-5 py-2.5 text-sm font-mono transition-colors cursor-pointer ${
              activeTab === "fields"
                ? "text-indigo-400 border-b-2 border-indigo-400"
                : "text-text-muted hover:text-foreground"
            }`}
          >
            Schema Fields
          </button>
          <button
            onClick={() => setActiveTab("networks")}
            className={`px-5 py-2.5 text-sm font-mono transition-colors cursor-pointer ${
              activeTab === "networks"
                ? "text-indigo-400 border-b-2 border-indigo-400"
                : "text-text-muted hover:text-foreground"
            }`}
          >
            Networks & Retention
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 custom-scrollbar">
          {activeTab === "fields" && (
            <div className="space-y-2">
              {fields.map((field, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <input
                    value={field.name}
                    onChange={(e) => {
                      const next = [...fields];
                      next[i] = { ...next[i], name: e.target.value };
                      setFieldsState(next);
                    }}
                    placeholder="Field name"
                    className="flex-1 bg-background border border-border-prominent rounded-lg px-3 py-1.5 text-sm text-foreground font-mono focus:outline-none focus:border-indigo-500/50"
                  />
                  <input
                    value={field.data_type}
                    onChange={(e) => {
                      const next = [...fields];
                      next[i] = { ...next[i], data_type: e.target.value };
                      setFieldsState(next);
                    }}
                    placeholder="Type"
                    className="w-28 bg-background border border-border-prominent rounded-lg px-3 py-1.5 text-sm text-foreground font-mono focus:outline-none focus:border-indigo-500/50"
                  />
                  <button
                    onClick={() => setFieldsState(fields.filter((_, j) => j !== i))}
                    className="p-1 text-text-muted hover:text-rose-400 transition-colors cursor-pointer"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              ))}
              <button
                onClick={() => setFieldsState([...fields, { name: "", data_type: "" }])}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-mono cursor-pointer flex items-center gap-1 mt-2"
              >
                <Plus className="size-3" /> Add field
              </button>
            </div>
          )}

          {activeTab === "networks" && (
            <div className="space-y-3">
              {editNetworks.map((net, i) => (
                <div key={net.network_id} className="flex items-center gap-3">
                  <label className="flex items-center gap-2 cursor-pointer min-w-[140px]">
                    <input
                      type="checkbox"
                      checked={net.selected}
                      onChange={(e) => {
                        const next = [...editNetworks];
                        next[i] = { ...next[i], selected: e.target.checked };
                        setEditNetworks(next);
                      }}
                      className="rounded border-border"
                    />
                    <span className="text-sm font-mono text-foreground">{net.network_name}</span>
                  </label>
                  {net.selected && (
                    <input
                      value={net.retention}
                      onChange={(e) => {
                        const next = [...editNetworks];
                        next[i] = { ...next[i], retention: e.target.value };
                        setEditNetworks(next);
                      }}
                      placeholder="Retention (e.g. 30 days)"
                      className="flex-1 bg-background border border-border-prominent rounded-lg px-3 py-1.5 text-sm text-foreground font-mono focus:outline-none focus:border-indigo-500/50"
                    />
                  )}
                </div>
              ))}
              {editNetworks.length === 0 && !isAdmin && (
                <p className="text-sm text-text-faint italic">No networks configured. Ask an admin to add networks.</p>
              )}
              {isAdmin && (
                <div className="flex items-center gap-2 pt-2 border-t border-border mt-2">
                  <input
                    value={newNetworkName}
                    onChange={(e) => setNewNetworkName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && newNetworkName.trim()) {
                        createNet.mutate({ name: newNetworkName.trim() }, {
                          onSuccess: () => setNewNetworkName(""),
                        });
                      }
                    }}
                    placeholder="New network name..."
                    className="flex-1 bg-background border border-border-prominent rounded-lg px-3 py-1.5 text-sm text-foreground font-mono focus:outline-none focus:border-indigo-500/50"
                  />
                  <button
                    onClick={() => {
                      if (newNetworkName.trim()) {
                        createNet.mutate({ name: newNetworkName.trim() }, {
                          onSuccess: () => setNewNetworkName(""),
                        });
                      }
                    }}
                    disabled={!newNetworkName.trim() || createNet.isPending}
                    className="p-1.5 text-indigo-400 hover:text-indigo-300 disabled:opacity-30 cursor-pointer"
                  >
                    <Plus className="size-3.5" />
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 p-5 border-t border-border shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-text-secondary hover:text-foreground transition-colors rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={setFields.isPending || setNetworks.isPending}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {(setFields.isPending || setNetworks.isPending) ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
