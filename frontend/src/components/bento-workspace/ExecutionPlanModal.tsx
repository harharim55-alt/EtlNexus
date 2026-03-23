import { useEffect, useState } from "react";
import { X, GitMerge, ScanEye } from "lucide-react";
import { formatDuration } from "@/lib/format";
import { NODE_STYLES } from "./execution-plan/plan-constants";
import { TreeNode, treeStyles } from "./execution-plan/PlanTree";
import { NodeDetailModal } from "./execution-plan/PlanFormatters";
import { usePannable } from "./execution-plan/usePannable";
import { useOverview } from "./execution-plan/useOverview";
import type {
  ExecutionPlanResponse,
  ExecutionPlanNode,
} from "@/types/execution-plan";

/* ── Props ─────────────────────────────────────────────────────────── */

interface ExecutionPlanModalProps {
  open: boolean;
  onClose: () => void;
  data: ExecutionPlanResponse;
}

/* ── Constants ─────────────────────────────────────────────────────── */

const DOT_GRID_STYLE: React.CSSProperties = {
  backgroundImage:
    "radial-gradient(rgba(148,163,184,0.07) 1px, transparent 1px)",
  backgroundSize: "24px 24px",
};

const LEGEND: { type: ExecutionPlanNode["type"]; label: string }[] = [
  { type: "read", label: "Read" },
  { type: "write", label: "Write" },
  { type: "shuffle", label: "Shuffle" },
  { type: "transform", label: "Transform" },
];

/* ── Helpers ───────────────────────────────────────────────────────── */

function countNodes(node: ExecutionPlanNode): Record<string, number> {
  const counts: Record<string, number> = {};
  function walk(n: ExecutionPlanNode) {
    counts[n.type] = (counts[n.type] || 0) + 1;
    for (const child of n.children) walk(child);
  }
  walk(node);
  return counts;
}

/* ── Modal ─────────────────────────────────────────────────────────── */

export function ExecutionPlanModal({
  open,
  onClose,
  data,
}: ExecutionPlanModalProps) {
  const [expandedNode, setExpandedNode] = useState<ExecutionPlanNode | null>(
    null,
  );
  const panRef = usePannable<HTMLDivElement>();
  const { containerRef, treeRef, isOverview, toggleOverview, scale } =
    useOverview();

  // Reset when modal closes
  useEffect(() => {
    if (!open) setExpandedNode(null);
  }, [open]);

  // Escape key
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open || !data.execution_plan) return null;

  const nodeCounts = countNodes(data.execution_plan);
  const totalNodes = Object.values(nodeCounts).reduce((a, b) => a + b, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/85 backdrop-blur-md animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal panel */}
      <div className="relative w-full max-w-[92vw] h-[88vh] bg-[#0a0a0f] border border-white/[0.06] rounded-2xl shadow-2xl shadow-black/60 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <style>{treeStyles}</style>

        {/* ── Header ──────────────────────────────────────────────── */}
        <div className="px-6 py-3.5 border-b border-white/[0.06] bg-[#0e0e14] flex items-center gap-4 shrink-0">
          {/* Icon + Title */}
          <div className="size-8 bg-indigo-500/10 border border-indigo-500/20 rounded-lg flex items-center justify-center shrink-0">
            <GitMerge className="size-4 text-indigo-400" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-white tracking-tight truncate">
              Logical Execution DAG
            </h2>
            <p className="text-[10px] text-slate-600 font-mono mt-0.5">
              Physical query plan with metrics
            </p>
          </div>

          {/* DAG + duration pills */}
          <div className="w-px h-5 bg-white/[0.06] mx-1" />
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500">
            <span className="px-2 py-1 rounded bg-white/[0.03] border border-white/[0.05]">
              {data.dag_id}
            </span>
            {data.duration_seconds != null && (
              <span className="px-2 py-1 rounded bg-white/[0.03] border border-white/[0.05]">
                {formatDuration(data.duration_seconds)}
              </span>
            )}
          </div>

          <div className="flex-1" />

          {/* Overview toggle */}
          <button
            type="button"
            onClick={toggleOverview}
            className={`text-[9px] font-mono px-2 py-1 rounded border transition-all cursor-pointer flex items-center gap-1.5 ${
              isOverview
                ? "text-indigo-400 bg-indigo-500/10 border-indigo-500/30"
                : "text-slate-500 bg-white/[0.03] border-white/5 hover:border-indigo-500/30 hover:text-indigo-400 hover:bg-indigo-500/10"
            }`}
          >
            <ScanEye className="w-3 h-3" />
            Overview
          </button>

          {/* Node count stats */}
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[9px] font-mono text-slate-600">
              {totalNodes} node{totalNodes !== 1 ? "s" : ""}
            </span>
            <div className="w-px h-3 bg-white/[0.06]" />
            <div className="flex items-center gap-1.5">
              {LEGEND.map(({ type, label }) => {
                const count = nodeCounts[type] || 0;
                if (count === 0) return null;
                const s = NODE_STYLES[type];
                return (
                  <span
                    key={type}
                    className={`flex items-center gap-1 text-[8px] font-mono px-1.5 py-0.5 rounded ${s.bg} ${s.text}`}
                  >
                    <span
                      className={`inline-block w-1.5 h-1.5 rounded-full ${s.border.replace("border-", "bg-").replace("/30", "")}`}
                    />
                    {count} {label}
                  </span>
                );
              })}
            </div>
          </div>

          {/* Close */}
          <button
            onClick={onClose}
            className="p-1.5 text-slate-600 hover:text-white hover:bg-white/5 rounded-lg transition-all border border-transparent hover:border-white/[0.06]"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* ── Body (scrollable tree canvas) ───────────────────────── */}
        <div
          ref={(node) => {
            panRef(node);
            containerRef(node);
          }}
          className="flex-1 overflow-auto custom-scrollbar relative"
          style={DOT_GRID_STYLE}
        >
          <div
            ref={treeRef}
            className="relative min-w-max flex justify-center p-10"
            style={
              isOverview
                ? {
                    transform: `scale(${scale})`,
                    transformOrigin: "center top",
                    minWidth: "unset",
                  }
                : undefined
            }
          >
            <div className="tree-container">
              <ul>
                <TreeNode
                  node={data.execution_plan}
                  onExpand={setExpandedNode}
                />
              </ul>
            </div>
          </div>
        </div>

        {/* ── Floating legend ─────────────────────────────────────── */}
        <div className="absolute bottom-4 right-4 flex items-center gap-2 px-3 py-2 bg-black/70 backdrop-blur-sm border border-white/[0.06] rounded-lg">
          {LEGEND.map(({ type, label }) => {
            const s = NODE_STYLES[type];
            const Icon = s.icon;
            return (
              <span
                key={type}
                className="flex items-center gap-1.5 text-[9px] font-mono text-slate-500"
              >
                <Icon className={`w-3 h-3 ${s.text}`} />
                {label}
              </span>
            );
          })}
        </div>
      </div>

      {/* Node detail modal (layered on top) */}
      {expandedNode && (
        <NodeDetailModal
          node={expandedNode}
          onClose={() => setExpandedNode(null)}
        />
      )}
    </div>
  );
}
