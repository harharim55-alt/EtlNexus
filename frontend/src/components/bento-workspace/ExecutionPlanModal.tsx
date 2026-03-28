import { useEffect, useState } from "react";
import { X, GitMerge, ScanEye, Search } from "lucide-react";
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
    "radial-gradient(rgba(128,128,128,0.07) 1px, transparent 1px)",
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

function countMatches(node: ExecutionPlanNode, query: string): number {
  if (!query) return 0;
  const q = query.toLowerCase();
  let count =
    node.name.toLowerCase().includes(q) ||
    (node.detail ?? "").toLowerCase().includes(q)
      ? 1
      : 0;
  for (const child of node.children) count += countMatches(child, q);
  return count;
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
  const [searchQuery, setSearchQuery] = useState("");
  const panRef = usePannable<HTMLDivElement>();
  const { containerRef, treeRef, isOverview, toggleOverview, scale } =
    useOverview();

  // Reset when modal closes
  useEffect(() => {
    if (!open) {
      setExpandedNode(null);
      setSearchQuery("");
    }
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
  const matchCount = countMatches(data.execution_plan, searchQuery);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/85 backdrop-blur-md animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal panel */}
      <div className="relative w-full max-w-[92vw] h-[88vh] bg-surface-modal border border-border rounded-2xl shadow-2xl shadow-black/60 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <style>{treeStyles}</style>

        {/* ── Header ──────────────────────────────────────────────── */}
        <div className="px-6 py-3.5 border-b border-border bg-surface-modal-header flex items-center gap-4 shrink-0">
          {/* Icon + Title */}
          <div className="size-8 bg-indigo-500/10 border border-indigo-500/20 rounded-lg flex items-center justify-center shrink-0">
            <GitMerge className="size-4 text-indigo-400" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-foreground tracking-tight truncate">
              Logical Execution DAG
            </h2>
            <p className="text-[10px] text-text-faint font-mono mt-0.5">
              Physical query plan with metrics
            </p>
          </div>

          {/* DAG + duration pills */}
          <div className="w-px h-5 bg-hover-bg-strong mx-1" />
          <div className="flex items-center gap-2 text-[10px] font-mono text-text-muted">
            <span className="px-2 py-1 rounded bg-hover-bg border border-border">
              {data.dag_id}
            </span>
            {data.duration_seconds != null && (
              <span className="px-2 py-1 rounded bg-hover-bg border border-border">
                {formatDuration(data.duration_seconds)}
              </span>
            )}
          </div>

          {/* Search bar */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-500" />
              <input
                type="text"
                placeholder="Search nodes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-7 w-44 rounded bg-zinc-800 border border-zinc-700 pl-7 pr-2 text-xs text-zinc-300 placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            {matchCount > 0 && (
              <span className="text-xs text-indigo-400">{matchCount} found</span>
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
                : "text-text-muted bg-hover-bg border-border hover:border-indigo-500/30 hover:text-indigo-400 hover:bg-indigo-500/10"
            }`}
          >
            <ScanEye className="w-3 h-3" />
            Overview
          </button>

          {/* Node count stats */}
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[9px] font-mono text-text-faint">
              {totalNodes} node{totalNodes !== 1 ? "s" : ""}
            </span>
            <div className="w-px h-3 bg-hover-bg-strong" />
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
            className="p-1.5 text-text-faint hover:text-foreground hover:bg-hover-bg rounded-lg transition-all border border-transparent hover:border-border"
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
                  searchQuery={searchQuery}
                />
              </ul>
            </div>
          </div>
        </div>

        {/* ── Floating legend ─────────────────────────────────────── */}
        <div className="absolute bottom-4 right-4 flex items-center gap-2 px-3 py-2 bg-black/70 backdrop-blur-sm border border-border rounded-lg">
          {LEGEND.map(({ type, label }) => {
            const s = NODE_STYLES[type];
            const Icon = s.icon;
            return (
              <span
                key={type}
                className="flex items-center gap-1.5 text-[9px] font-mono text-text-muted"
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
