import { useState } from "react";
import { X } from "lucide-react";
import { NODE_STYLES } from "./plan-constants";
import { FormattedDetail, RawDetail } from "./formatters";
import type { ExecutionPlanNode } from "@/types/execution-plan";

// ── Modal ────────────────────────────────────────────────────────

export function NodeDetailModal({
  node,
  onClose,
}: {
  node: ExecutionPlanNode;
  onClose: () => void;
}) {
  const [activeTab, setActiveTab] = useState<"formatted" | "raw">("formatted");
  const style = NODE_STYLES[node.type] ?? NODE_STYLES.transform;
  const Icon = style.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-lg bg-[#141419] border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-xl border ${style.bg} ${style.border}`}
            >
              <Icon className={`w-4 h-4 ${style.text}`} />
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-semibold ${style.text}`}>
                {node.name}
              </span>
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 bg-white/5 px-1.5 py-0.5 rounded">
                {node.type}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab bar */}
        <div className="px-6 py-2 bg-black/20 border-b border-white/[0.04] flex gap-1">
          <button
            onClick={() => setActiveTab("formatted")}
            className={`px-3 py-1.5 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors ${
              activeTab === "formatted"
                ? "bg-white/10 text-white"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            Formatted
          </button>
          <button
            onClick={() => setActiveTab("raw")}
            className={`px-3 py-1.5 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors ${
              activeTab === "raw"
                ? "bg-white/10 text-white"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            Raw
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 max-h-[60vh] overflow-y-auto">
          {activeTab === "formatted" ? (
            <FormattedDetail node={node} />
          ) : (
            <RawDetail node={node} />
          )}
        </div>
      </div>
    </div>
  );
}
