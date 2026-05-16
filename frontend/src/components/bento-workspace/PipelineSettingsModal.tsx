import { useState, useEffect } from "react";
import { X, Plus, Trash2, Check } from "lucide-react";
import { useTags, useCreateTag, useSetPipelineTags } from "@/hooks/use-tags";
import { useNetworks, useCreateNetwork } from "@/hooks/use-networks";
import { usePipelineLogs, useCreatePipelineLog, useSetLogNetworks } from "@/hooks/use-pipeline-logs";
import { useAuthStore } from "@/stores/auth-store";
import type { PipelineDetail } from "@/types/pipeline";

interface PipelineSettingsModalProps {
  open: boolean;
  onClose: () => void;
  pipeline: PipelineDetail;
  onUpdate: (updates: Record<string, unknown>) => void;
  isSaving: boolean;
}

export function PipelineSettingsModal({
  open,
  onClose,
  pipeline,
  onUpdate,
  isSaving,
}: PipelineSettingsModalProps) {
  const { data: allTagsData } = useTags();
  const createTag = useCreateTag();
  const setTags = useSetPipelineTags(pipeline.id);
  const { data: networksData } = useNetworks();
  const { data: logsData } = usePipelineLogs(pipeline.id);
  const createNetwork = useCreateNetwork();
  const createLog = useCreatePipelineLog(pipeline.id);
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === "admin";

  const firstLog = logsData?.items?.[0] ?? null;
  const setLogNets = useSetLogNetworks(pipeline.id, firstLog?.id ?? "");

  const [scheduleType, setScheduleType] = useState(pipeline.schedule_type ?? "");
  const [topologyEnabled, setTopologyEnabled] = useState(pipeline.topology_enabled);
  const [importSnippet, setImportSnippet] = useState(pipeline.import_snippet ?? "");
  const [writesTo, setWritesTo] = useState<string[]>(pipeline.writes_to_manual ?? []);
  const [newWritesTo, setNewWritesTo] = useState("");
  const [newTagName, setNewTagName] = useState("");
  const [newNetworkName, setNewNetworkName] = useState("");
  const allTags = allTagsData?.items ?? [];
  const selectedTagIds = new Set((pipeline.tags ?? []).map((t) => t.id));
  const allNetworks = networksData?.items ?? [];
  const selectedNetworkIds = new Set(firstLog?.networks.map((n) => n.network_id) ?? []);

  // Reset state when pipeline changes
  useEffect(() => {
    setScheduleType(pipeline.schedule_type ?? "");
    setImportSnippet(pipeline.import_snippet ?? "");
    setTopologyEnabled(pipeline.topology_enabled);
    setWritesTo(pipeline.writes_to_manual ?? []);
  }, [pipeline.id]);

  if (!open) return null;

  const toggleTag = (tagId: string) => {
    const next = new Set(selectedTagIds);
    if (next.has(tagId)) next.delete(tagId);
    else next.add(tagId);
    setTags.mutate(Array.from(next));
  };

  const toggleNetwork = (networkId: string) => {
    if (!firstLog) {
      // Auto-create a log then toggle
      createLog.mutate({ name: "Default" }, {
        onSuccess: () => {
          // After log creation, logs will refetch; user can toggle again
        },
      });
      return;
    }
    const currentNets = firstLog.networks.map((n) => ({
      network_id: n.network_id,
      retention: n.retention ?? undefined,
    }));
    const exists = currentNets.find((n) => n.network_id === networkId);
    const next = exists
      ? currentNets.filter((n) => n.network_id !== networkId)
      : [...currentNets, { network_id: networkId }];
    setLogNets.mutate(next);
  };

  const handleCreateNetwork = () => {
    if (!newNetworkName.trim()) return;
    createNetwork.mutate({ name: newNetworkName.trim() }, {
      onSuccess: () => setNewNetworkName(""),
    });
  };

  const handleCreateTag = () => {
    if (!newTagName.trim()) return;
    createTag.mutate(newTagName.trim(), {
      onSuccess: (tag) => {
        const next = new Set(selectedTagIds);
        next.add(tag.id);
        setTags.mutate(Array.from(next));
        setNewTagName("");
      },
    });
  };

  const addWritesTo = () => {
    if (newWritesTo.trim() && !writesTo.includes(newWritesTo.trim())) {
      setWritesTo([...writesTo, newWritesTo.trim()]);
      setNewWritesTo("");
    }
  };

  const handleSave = () => {
    const updates: Record<string, unknown> = {};
    if (scheduleType !== (pipeline.schedule_type ?? ""))
      updates.schedule_type = scheduleType || null;
    if (importSnippet !== (pipeline.import_snippet ?? ""))
      updates.import_snippet = importSnippet || null;
    if (topologyEnabled !== pipeline.topology_enabled)
      updates.topology_enabled = topologyEnabled;

    const origWrites = JSON.stringify(pipeline.writes_to_manual ?? []);
    if (JSON.stringify(writesTo) !== origWrites)
      updates.writes_to_manual = writesTo.length > 0 ? writesTo : null;

    if (Object.keys(updates).length > 0) {
      onUpdate(updates);
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-in fade-in duration-150">
      <div className="bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl animate-in zoom-in-95 duration-200 max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-border shrink-0">
          <h2 className="text-lg font-semibold text-foreground">Settings</h2>
          <button onClick={onClose} className="p-1 text-text-muted hover:text-foreground transition-colors cursor-pointer">
            <X className="size-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6 custom-scrollbar">
          {/* Tags */}
          <Section label="Tags">
            <div className="flex flex-wrap gap-1.5 mb-2">
              {allTags.map((tag) => (
                <button
                  key={tag.id}
                  onClick={() => toggleTag(tag.id)}
                  className={`text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer flex items-center gap-1 ${
                    selectedTagIds.has(tag.id)
                      ? "text-amber-300 bg-amber-500/15 border-amber-500/30"
                      : "text-text-muted bg-hover-bg border-border hover:border-border-prominent"
                  }`}
                >
                  {selectedTagIds.has(tag.id) && <Check className="size-2.5" />}
                  {tag.name}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1.5">
              <input
                value={newTagName}
                onChange={(e) => setNewTagName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateTag()}
                placeholder="Create new tag..."
                className="flex-1 bg-background border border-border-prominent rounded-lg px-3 py-1.5 text-xs font-mono text-foreground focus:outline-none focus:border-indigo-500/50"
              />
              <button
                onClick={handleCreateTag}
                disabled={!newTagName.trim() || createTag.isPending}
                className="p-1.5 text-indigo-400 hover:text-indigo-300 disabled:opacity-30 cursor-pointer"
              >
                <Plus className="size-3.5" />
              </button>
            </div>
          </Section>

          {/* Networks */}
          <Section label="Networks">
            <div className="flex flex-wrap gap-1.5 mb-2">
              {allNetworks.map((net) => (
                <button
                  key={net.id}
                  onClick={() => toggleNetwork(net.id)}
                  disabled={!firstLog && !createLog.isPending}
                  className={`text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer flex items-center gap-1 ${
                    selectedNetworkIds.has(net.id)
                      ? "text-teal-300 bg-teal-500/15 border-teal-500/30"
                      : "text-text-muted bg-hover-bg border-border hover:border-border-prominent"
                  }`}
                >
                  {selectedNetworkIds.has(net.id) && <Check className="size-2.5" />}
                  {net.name}
                </button>
              ))}
            </div>
            {!firstLog && (
              <p className="text-[10px] text-text-faint mb-2">A default log will be created when you select a network.</p>
            )}
            {isAdmin && (
              <div className="flex items-center gap-1.5">
                <input
                  value={newNetworkName}
                  onChange={(e) => setNewNetworkName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreateNetwork()}
                  placeholder="Create new network..."
                  className="flex-1 bg-background border border-border-prominent rounded-lg px-3 py-1.5 text-xs font-mono text-foreground focus:outline-none focus:border-indigo-500/50"
                />
                <button
                  onClick={handleCreateNetwork}
                  disabled={!newNetworkName.trim() || createNetwork.isPending}
                  className="p-1.5 text-indigo-400 hover:text-indigo-300 disabled:opacity-30 cursor-pointer"
                >
                  <Plus className="size-3.5" />
                </button>
              </div>
            )}
          </Section>

          {/* Schedule Type */}
          <Section label="Schedule">
            <select
              value={scheduleType}
              onChange={(e) => { setScheduleType(e.target.value);}}
              className="w-full bg-background border border-border-prominent rounded-lg px-3 py-2 text-sm text-foreground font-mono focus:outline-none focus:border-indigo-500/50 cursor-pointer"
            >
              <option value="">Not set</option>
              <option value="daily">Daily</option>
              <option value="hourly">Hourly</option>
              <option value="stream">Stream</option>
            </select>
          </Section>

          {/* Import Snippet */}
          <Section label="Import Snippet">
            <textarea
              value={importSnippet}
              onChange={(e) => { setImportSnippet(e.target.value); }}
              rows={3}
              placeholder="Leave empty for auto-generated snippet"
              className="w-full bg-background border border-border-prominent rounded-lg px-3 py-2 text-sm text-foreground font-mono focus:outline-none focus:border-indigo-500/50 resize-none"
            />
            <p className="text-[10px] text-text-faint mt-1">When set, replaces the auto-generated Import & Consume code.</p>
          </Section>

          {/* Writes To */}
          <Section label="Writes To">
            <div className="space-y-1.5">
              {writesTo.map((item, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="flex-1 text-xs font-mono text-foreground bg-background px-3 py-1.5 rounded-lg border border-border truncate">
                    {item}
                  </span>
                  <button
                    onClick={() => { setWritesTo(writesTo.filter((_, j) => j !== i));}}
                    className="p-1 text-text-muted hover:text-rose-400 cursor-pointer"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              ))}
              <div className="flex items-center gap-1.5">
                <input
                  value={newWritesTo}
                  onChange={(e) => setNewWritesTo(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addWritesTo()}
                  placeholder="Add table name..."
                  className="flex-1 bg-background border border-border-prominent rounded-lg px-3 py-1.5 text-xs font-mono text-foreground focus:outline-none focus:border-indigo-500/50"
                />
                <button
                  onClick={addWritesTo}
                  disabled={!newWritesTo.trim()}
                  className="p-1.5 text-indigo-400 hover:text-indigo-300 disabled:opacity-30 cursor-pointer"
                >
                  <Plus className="size-3.5" />
                </button>
              </div>
            </div>
          </Section>

          {/* Topology */}
          <Section label="Pipeline Topology">
            <button
              onClick={() => { setTopologyEnabled(!topologyEnabled);}}
              className={`px-4 py-2 rounded-lg border text-sm font-mono transition-all cursor-pointer ${
                topologyEnabled
                  ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                  : "text-text-muted bg-hover-bg border-border"
              }`}
            >
              {topologyEnabled ? "Enabled" : "Disabled"}
            </button>
          </Section>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-5 border-t border-border shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-text-secondary hover:text-foreground transition-colors rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {isSaving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[10px] font-mono uppercase tracking-widest text-text-faint block mb-2">
        {label}
      </label>
      {children}
    </div>
  );
}
