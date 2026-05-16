import { useState } from "react";
import { X } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/api/client";
import { toast } from "sonner";
import type { PipelineDetail } from "@/types/pipeline";

interface CreateDataProductModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (product: PipelineDetail) => void;
}

export function CreateDataProductModal({ open, onClose, onCreated }: CreateDataProductModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [scheduleType, setScheduleType] = useState<string>("");
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post<PipelineDetail>("/data-products", {
        name,
        description: description || null,
        schedule_type: scheduleType || null,
      });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["data-products"] });
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      toast.success(`Data product "${name}" created`);
      onCreated(data);
      resetForm();
    },
    onError: () => {
      toast.error("Failed to create data product");
    },
  });

  const resetForm = () => {
    setName("");
    setDescription("");
    setScheduleType("");
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-in fade-in duration-150">
      <div className="bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl animate-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between p-5 border-b border-border">
          <h2 className="text-lg font-semibold text-foreground">New Data Product</h2>
          <button onClick={onClose} className="p-1 text-text-muted hover:text-foreground transition-colors cursor-pointer">
            <X className="size-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label className="text-[11px] font-mono uppercase tracking-widest text-text-muted block mb-1.5">
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. PortScanCollector"
              className="w-full bg-background border border-border-prominent rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50"
            />
          </div>

          <div>
            <label className="text-[11px] font-mono uppercase tracking-widest text-text-muted block mb-1.5">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value.slice(0, 270))}
              maxLength={270}
              rows={3}
              placeholder="Brief description..."
              className="w-full bg-background border border-border-prominent rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 resize-none"
            />
            <span className="text-[10px] text-text-faint font-mono">{description.length}/270</span>
          </div>

          <div>
            <label className="text-[11px] font-mono uppercase tracking-widest text-text-muted block mb-1.5">
              Schedule
            </label>
            <select
              value={scheduleType}
              onChange={(e) => setScheduleType(e.target.value)}
              className="w-full bg-background border border-border-prominent rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-indigo-500/50"
            >
              <option value="">Select schedule...</option>
              <option value="daily">Daily</option>
              <option value="hourly">Hourly</option>
              <option value="stream">Stream</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-2 p-5 border-t border-border">
          <button
            onClick={() => { onClose(); resetForm(); }}
            className="px-4 py-2 text-sm text-text-secondary hover:text-foreground transition-colors rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={() => createMutation.mutate()}
            disabled={!name.trim() || createMutation.isPending}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {createMutation.isPending ? "Creating..." : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
