import { useEffect, useCallback, useMemo, useState } from "react";
import { X, GitFork, Lock, Sparkles, Radio, Loader2 } from "lucide-react";
import { useUpstreamTopology } from "@/hooks/use-upstream-topology";
import { usePipelineStore } from "@/stores/pipeline-store";
import { getStatusStyle, STATUS_CONFIG } from "@/lib/status-config";
import { useEdgeDrawing } from "./hooks/useEdgeDrawing";
import { stripDummy } from "@/lib/format";
import type { UpstreamNode, UpstreamEdge } from "@/types/topology";

/* ── Props ─────────────────────────────────────────────────────────── */

interface UpstreamTopologyModalProps {
  open: boolean;
  onClose: () => void;
  pipelineId: string;
}

/* ── Module-level constants ────────────────────────────────────────── */

const DOT_GRID_STYLE: React.CSSProperties = {
  backgroundImage: "radial-gradient(rgba(148,163,184,0.07) 1px, transparent 1px)",
  backgroundSize: "24px 24px",
};

const SVG_OVERLAY_STYLE: React.CSSProperties = {
  width: "100%",
  height: "100%",
  overflow: "visible",
};

/* ── Helpers ───────────────────────────────────────────────────────── */

function statusSummary(nodes: UpstreamNode[]) {
  const counts: Record<string, number> = {};
  for (const n of nodes) {
    const s = n.status || "unknown";
    counts[s] = (counts[s] || 0) + 1;
  }
  return counts;
}

/** Determine the dominant incoming edge type for a node */
function getNodeEdgeType(node: UpstreamNode, edges: UpstreamEdge[]): "needs" | "prefers" | "current" | "bouncer" | "root" {
  if (node.is_current) return "current";
  if (node.is_bouncer) return "bouncer";
  const incoming = edges.filter((e) => e.target_task_id === node.task_id);
  if (incoming.length === 0) return "root";
  if (incoming.some((e) => e.edge_type === "needs")) return "needs";
  return "prefers";
}

/** Check if a node is connected to the hovered node */
function isConnectedToHovered(nodeTaskId: string, hoveredNode: string | null, edges: UpstreamEdge[]): boolean {
  if (hoveredNode === null) return false;
  return hoveredNode === nodeTaskId || edges.some((e) =>
    (e.source_task_id === hoveredNode && e.target_task_id === nodeTaskId) ||
    (e.target_task_id === hoveredNode && e.source_task_id === nodeTaskId)
  );
}

/* ── Main Modal ────────────────────────────────────────────────────── */

export function UpstreamTopologyModal({ open, onClose, pipelineId }: UpstreamTopologyModalProps) {
  const [activeDagId, setActiveDagId] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const { data, isLoading } = useUpstreamTopology(pipelineId, activeDagId, open);
  const setSelectedPipelineId = usePipelineStore((s) => s.setSelectedPipelineId);

  const { containerRef, edgePaths, setNodeRef } = useEdgeDrawing(open, data?.edges);

  // The resolved DAG from the response (backend defaults to first DAG when activeDagId is null)
  const displayDagId = activeDagId ?? data?.dag_id ?? null;

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setActiveDagId(null);
      setHoveredNode(null);
    }
  }, [open]);

  // Escape key
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  const handleNodeClick = useCallback(
    (node: UpstreamNode) => {
      if (node.is_current || !node.pipeline_id) return;
      setSelectedPipelineId(node.pipeline_id);
      onClose();
    },
    [setSelectedPipelineId, onClose],
  );

  const handleMouseEnter = useCallback((taskId: string) => {
    setHoveredNode(taskId);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setHoveredNode(null);
  }, []);

  // Group nodes by depth (reversed: max_depth on left, 0 on right)
  const { columns, maxDepth } = useMemo(() => {
    if (!data) return { columns: [] as UpstreamNode[][], maxDepth: 0 };
    const md = data.max_depth;
    const cols: UpstreamNode[][] = Array.from({ length: md + 1 }, () => []);
    for (const node of data.nodes) {
      cols[node.depth].push(node);
    }
    for (const col of cols) {
      col.sort((a, b) => a.task_id.localeCompare(b.task_id));
    }
    return { columns: cols, maxDepth: md };
  }, [data]);

  // Derived node lists and summary
  const { dagIds, etlNodes, bouncerNodes, summary } = useMemo(() => {
    const dIds = data?.dag_ids ?? [];
    const etls = data ? data.nodes.filter((n) => !n.is_bouncer) : [];
    const bouncers = data ? data.nodes.filter((n) => n.is_bouncer) : [];
    const sum = data ? statusSummary(etls) : {};
    return { dagIds: dIds, etlNodes: etls, bouncerNodes: bouncers, summary: sum };
  }, [data]);

  // Pre-compute highlight/dim state per node
  const nodeRenderState = useMemo(() => {
    if (!data) return new Map<string, { isHighlighted: boolean; isDimmed: boolean }>();
    const map = new Map<string, { isHighlighted: boolean; isDimmed: boolean }>();
    for (const node of data.nodes) {
      const connected = isConnectedToHovered(node.task_id, hoveredNode, data.edges);
      map.set(node.task_id, {
        isHighlighted: hoveredNode !== null && connected,
        isDimmed: hoveredNode !== null && !connected,
      });
    }
    return map;
  }, [data, hoveredNode]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/85 backdrop-blur-md animate-in fade-in duration-200" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-[92vw] h-[88vh] bg-[#0a0a0f] border border-white/[0.06] rounded-2xl shadow-2xl shadow-black/60 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">

        {/* ── Header ──────────────────────────────────────────────── */}
        <div className="px-6 py-3.5 border-b border-white/[0.06] bg-[#0e0e14] flex items-center gap-4 shrink-0">
          {/* Icon + Title */}
          <div className="size-8 bg-indigo-500/10 border border-indigo-500/20 rounded-lg flex items-center justify-center shrink-0">
            <GitFork className="size-4 text-indigo-400" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-white tracking-tight truncate">
              {data?.pipeline_task_id?.replace(/_/g, " ") ?? "Loading..."}
            </h2>
            <p className="text-[10px] text-slate-600 font-mono mt-0.5">
              Upstream Dependency Graph
            </p>
          </div>

          {/* DAG selector tabs */}
          {dagIds.length > 1 && (
            <>
              <div className="w-px h-5 bg-white/[0.06] mx-1" />
              <div className="flex bg-white/[0.03] rounded-lg p-0.5 border border-white/[0.05]">
                {dagIds.map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setActiveDagId(id)}
                    className={`px-3 py-1.5 text-[10px] font-mono rounded-md transition-all duration-200 ${
                      displayDagId === id
                        ? "bg-white/[0.08] text-white shadow-sm"
                        : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    {id.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </>
          )}
          {dagIds.length === 1 && (
            <>
              <div className="w-px h-5 bg-white/[0.06] mx-1" />
              <span className="text-[10px] font-mono text-slate-500 px-2 py-1 rounded bg-white/[0.03] border border-white/[0.05]">
                {dagIds[0].replace(/_/g, " ")}
              </span>
            </>
          )}

          <div className="flex-1" />

          {/* Stats pills */}
          {data && (
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[9px] font-mono text-slate-600">
                {etlNodes.length} task{etlNodes.length !== 1 ? "s" : ""}
                {bouncerNodes.length > 0 && (<span className="text-slate-700"> + {bouncerNodes.length} bouncer{bouncerNodes.length !== 1 ? "s" : ""}</span>)}
                <span className="text-slate-700 ml-1">{maxDepth + 1} layer{maxDepth !== 0 ? "s" : ""}</span>
              </span>
              <div className="w-px h-3 bg-white/[0.06]" />
              <div className="flex items-center gap-1">
                {Object.entries(summary).map(([status, count]) => {
                  const cfg = getStatusStyle(status);
                  return (
                    <span key={status} className={`flex items-center gap-1 text-[8px] font-mono px-1.5 py-0.5 rounded ${cfg.text} ${cfg.bg}`}>
                      <span className={`inline-block w-1.5 h-1.5 rounded-full ${cfg.dot.replace(" animate-pulse", "")}`} />
                      {count}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {/* Close */}
          <button onClick={onClose} className="p-1.5 text-slate-600 hover:text-white hover:bg-white/5 rounded-lg transition-all border border-transparent hover:border-white/[0.06]">
            <X className="size-4" />
          </button>
        </div>

        {/* ── Body ────────────────────────────────────────────────── */}
        <div
          ref={containerRef}
          className="flex-1 overflow-auto custom-scrollbar relative"
          style={DOT_GRID_STYLE}
        >
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="size-5 text-indigo-400 animate-spin" />
                <span className="text-[10px] font-mono text-slate-600">Loading topology...</span>
              </div>
            </div>
          ) : !data || data.nodes.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="flex flex-col items-center gap-2">
                <GitFork className="size-5 text-slate-700" />
                <span className="text-[11px] text-slate-600 font-mono">No upstream dependencies</span>
              </div>
            </div>
          ) : (
            <div className="relative inline-flex items-stretch min-w-full min-h-full p-8">
              {/* SVG edge overlay */}
              <svg className="absolute inset-0 pointer-events-none" style={SVG_OVERLAY_STYLE}>
                <defs>
                  <filter id="edgeGlow">
                    <feGaussianBlur stdDeviation="2" result="blur" />
                    <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                  </filter>
                </defs>
                {edgePaths.map((ep, i) => {
                  const isHovered = hoveredNode !== null && (ep.sourceId === hoveredNode || ep.targetId === hoveredNode);
                  const isNeeds = ep.type === "needs";
                  return (
                    <g key={i}>
                      <path
                        d={ep.d}
                        fill="none"
                        stroke={isNeeds
                          ? (isHovered ? "rgba(251,146,60,0.55)" : "rgba(251,146,60,0.18)")
                          : (isHovered ? "rgba(56,189,248,0.5)" : "rgba(56,189,248,0.12)")
                        }
                        strokeWidth={isHovered ? 2.5 : (isNeeds ? 1.5 : 1)}
                        strokeDasharray={isNeeds ? undefined : "5 4"}
                        filter={isHovered ? "url(#edgeGlow)" : undefined}
                        className="transition-all duration-200"
                      />
                      {/* Connection dots */}
                      <circle cx={ep.sx} cy={ep.sy} r={isHovered ? 3 : 2} fill={isNeeds ? (isHovered ? "rgba(251,146,60,0.6)" : "rgba(251,146,60,0.25)") : (isHovered ? "rgba(56,189,248,0.5)" : "rgba(56,189,248,0.15)")} className="transition-all duration-200" />
                      <circle cx={ep.tx} cy={ep.ty} r={isHovered ? 3 : 2} fill={isNeeds ? (isHovered ? "rgba(251,146,60,0.6)" : "rgba(251,146,60,0.25)") : (isHovered ? "rgba(56,189,248,0.5)" : "rgba(56,189,248,0.15)")} className="transition-all duration-200" />
                    </g>
                  );
                })}
              </svg>

              {/* Columns: deepest first -> current last (bouncers are at max depth) */}
              {[...columns].reverse().map((col, colIdx) => {
                const depth = maxDepth - colIdx;
                if (col.length === 0) return null;
                const isCurrent = depth === 0;
                const hasBouncers = col.some((n) => n.is_bouncer);
                const isBouncerLayer = col.every((n) => n.is_bouncer);
                return (
                  <div key={depth} className="flex flex-col shrink-0 self-center" style={{ marginRight: colIdx < maxDepth ? 64 : 0 }}>
                    <div className={`rounded-xl border p-3 pb-2 ${
                      isCurrent
                        ? "border-indigo-500/20 bg-indigo-500/[0.03] shadow-[0_0_30px_rgba(99,102,241,0.06)]"
                        : isBouncerLayer
                          ? "border-teal-500/10 bg-teal-500/[0.02]"
                          : "border-white/[0.04] bg-white/[0.015]"
                    }`}>
                      {/* Column header */}
                      <div className="flex items-center justify-center gap-2 mb-3">
                        {isBouncerLayer && <Radio className="w-3 h-3 text-teal-400/50" />}
                        <span className={`text-[9px] font-mono uppercase tracking-[0.15em] ${
                          isCurrent ? "text-indigo-400/60" : isBouncerLayer ? "text-teal-400/50" : "text-slate-600"
                        }`}>
                          {isCurrent ? "Current" : isBouncerLayer ? "Bouncers" : hasBouncers ? `Layer ${depth} + Bouncers` : `Layer ${depth}`}
                        </span>
                        <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded-full ${
                          isCurrent ? "text-indigo-400/40 bg-indigo-500/8" : isBouncerLayer ? "text-teal-500/30 bg-teal-500/5" : "text-slate-700 bg-white/[0.03]"
                        }`}>
                          {col.length}
                        </span>
                      </div>
                      <div className="flex flex-col gap-2">
                        {col.map((node) => {
                          const rs = nodeRenderState.get(node.task_id) ?? { isHighlighted: false, isDimmed: false };
                          return (
                            <div
                              key={node.task_id}
                              ref={(el) => setNodeRef(node.task_id, el)}
                              onMouseEnter={() => handleMouseEnter(node.task_id)}
                              onMouseLeave={handleMouseLeave}
                            >
                              {node.is_bouncer ? (
                                <BouncerNodeCard
                                  node={node}
                                  isHighlighted={rs.isHighlighted}
                                  isDimmed={rs.isDimmed}
                                />
                              ) : (
                                <NodeCard
                                  node={node}
                                  edgeType={getNodeEdgeType(node, data.edges)}
                                  isHighlighted={rs.isHighlighted}
                                  isDimmed={rs.isDimmed}
                                  onClick={() => handleNodeClick(node)}
                                />
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Floating legend */}
          {data && data.nodes.length > 0 && (
            <div className="sticky bottom-3 left-3 z-10 inline-flex items-center gap-4 px-3 py-1.5 bg-black/50 backdrop-blur-sm rounded-lg border border-white/[0.06] ml-3 mb-3">
              <div className="flex items-center gap-1.5">
                <svg width="20" height="2" className="shrink-0"><line x1="0" y1="1" x2="20" y2="1" stroke="rgba(251,146,60,0.4)" strokeWidth="1.5" /></svg>
                <Lock className="w-2.5 h-2.5 text-orange-400/50" />
                <span className="text-[8px] font-mono text-slate-500">needs</span>
              </div>
              <div className="flex items-center gap-1.5">
                <svg width="20" height="2" className="shrink-0"><line x1="0" y1="1" x2="20" y2="1" stroke="rgba(56,189,248,0.3)" strokeWidth="1" strokeDasharray="4 3" /></svg>
                <Sparkles className="w-2.5 h-2.5 text-sky-400/50" />
                <span className="text-[8px] font-mono text-slate-500">prefers</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Radio className="w-2.5 h-2.5 text-teal-400/50" />
                <span className="text-[8px] font-mono text-slate-500">bouncer</span>
              </div>
              <div className="w-px h-3 bg-white/[0.06]" />
              {Object.entries(STATUS_CONFIG).filter(([k]) => k !== "unknown").map(([key, cfg]) => (
                <div key={key} className="flex items-center gap-1">
                  <span className={`inline-block w-1.5 h-1.5 rounded-full ${cfg.dot.replace(" animate-pulse", "")}`} />
                  <span className="text-[7px] font-mono text-slate-600">{cfg.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Node Card ─────────────────────────────────────────────────────── */

const EDGE_BORDER: Record<string, string> = {
  needs: "border-l-orange-400/50",
  prefers: "border-l-sky-400/40",
  current: "border-l-indigo-400/60",
  bouncer: "border-l-teal-400/50",
  root: "border-l-slate-600/30",
};

function NodeCard({
  node,
  edgeType,
  isHighlighted,
  isDimmed,
  onClick,
}: {
  node: UpstreamNode;
  edgeType: "needs" | "prefers" | "current" | "bouncer" | "root";
  isHighlighted: boolean;
  isDimmed: boolean;
  onClick: () => void;
}) {
  const displayName = stripDummy(node.pipeline_name ?? node.task_id).replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/_/g, " ");
  const isClickable = !node.is_current && !!node.pipeline_id;
  const cfg = getStatusStyle(node.status);

  return (
    <button
      type="button"
      onClick={isClickable ? onClick : undefined}
      disabled={!isClickable}
      className={`
        group/node flex items-center gap-2.5 w-[220px] px-3 py-2.5 rounded-lg border-l-[3px] border border-r border-t border-b
        text-left transition-all duration-200
        ${EDGE_BORDER[edgeType]}
        ${node.is_current
          ? "bg-indigo-500/[0.08] border-r-indigo-500/20 border-t-indigo-500/20 border-b-indigo-500/20 shadow-[0_0_24px_rgba(99,102,241,0.1)]"
          : "bg-[#0c0c11] border-r-white/[0.04] border-t-white/[0.04] border-b-white/[0.04] hover:border-r-white/10 hover:border-t-white/10 hover:border-b-white/10 hover:bg-white/[0.025]"
        }
        ${isClickable ? "cursor-pointer hover:-translate-y-[1px]" : "cursor-default"}
        ${isHighlighted && !node.is_current ? "!border-r-white/15 !border-t-white/15 !border-b-white/15 !bg-white/[0.04] -translate-y-[1px]" : ""}
        ${isDimmed ? "opacity-40" : ""}
      `}
    >
      <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${cfg.dot} ${cfg.glow}`} title={cfg.label} />
      <div className="min-w-0 flex-1">
        <span className={`text-[11px] font-medium block truncate ${
          node.is_current ? "text-indigo-300" : "text-slate-300 group-hover/node:text-slate-200"
        }`}>
          {displayName}
        </span>
        <span className="text-[9px] font-mono text-slate-600 block truncate">
          {node.task_id}
        </span>
      </div>
      <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded shrink-0 ${cfg.text} ${cfg.bg}`}>
        {cfg.label.toLowerCase()}
      </span>
    </button>
  );
}

/* ── Sensor Node Card ─────────────────────────────────────────────── */

function BouncerNodeCard({
  node,
  isHighlighted,
  isDimmed,
}: {
  node: UpstreamNode;
  isHighlighted: boolean;
  isDimmed: boolean;
}) {
  const displayName = stripDummy(node.pipeline_name ?? node.task_id).replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/_/g, " ");
  const cfg = getStatusStyle(node.status);

  return (
    <div
      className={`
        group/node flex items-center gap-2.5 w-[220px] px-3 py-2.5 rounded-lg border-l-[3px] border
        text-left transition-all duration-200
        border-l-teal-400/50
        bg-teal-500/[0.04] border-r-teal-500/10 border-t-teal-500/10 border-b-teal-500/10
        hover:border-r-teal-500/20 hover:border-t-teal-500/20 hover:border-b-teal-500/20 hover:bg-teal-500/[0.06]
        ${isHighlighted ? "!border-r-teal-400/25 !border-t-teal-400/25 !border-b-teal-400/25 !bg-teal-500/[0.08] -translate-y-[1px]" : ""}
        ${isDimmed ? "opacity-40" : ""}
      `}
    >
      <Radio className="w-3.5 h-3.5 text-teal-400/60 shrink-0" />
      <div className="min-w-0 flex-1">
        <span className="text-[11px] font-medium block truncate text-teal-200/70 group-hover/node:text-teal-200/90">
          {displayName}
        </span>
        <span className="text-[9px] font-mono text-slate-600 block truncate">
          {node.bouncer_name ?? node.task_id}
        </span>
      </div>
      <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${cfg.dot} ${cfg.glow}`} title={cfg.label} />
    </div>
  );
}
