import { useEffect, useCallback, useMemo, useState, useRef } from "react";
import { X, GitFork, Lock, Sparkles, Radio, Loader2, Download } from "lucide-react";
import { downloadAsSVG, downloadAsPNG, downloadAsInteractiveHTML } from "@/lib/export-visual";
import { useUpstreamTopology } from "@/hooks/use-upstream-topology";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useRunSelectorStore } from "@/stores/run-selector-store";
import { getStatusStyle, STATUS_CONFIG } from "@/lib/status-config";
import { useEdgeDrawing } from "./hooks/useEdgeDrawing";
import { NodeCard, BouncerNodeCard } from "./TopologyNodeCard";
import { TopologySvgEdges } from "./TopologySvgEdges";
import type { UpstreamNode, UpstreamEdge } from "@/types/topology";

/* ── Props ─────────────────────────────────────────────────────────── */

interface UpstreamTopologyModalProps {
  open: boolean;
  onClose: () => void;
  pipelineId: string;
}

/* ── Module-level constants ────────────────────────────────────────── */

const DOT_GRID_STYLE: React.CSSProperties = {
  backgroundImage: "radial-gradient(rgba(128,128,128,0.07) 1px, transparent 1px)",
  backgroundSize: "24px 24px",
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

/** Build adjacency map for O(1) hover connectivity lookups */
function buildAdjacencyMap(edges: UpstreamEdge[]): Map<string, Set<string>> {
  const map = new Map<string, Set<string>>();
  for (const edge of edges) {
    if (!map.has(edge.source_task_id)) map.set(edge.source_task_id, new Set());
    if (!map.has(edge.target_task_id)) map.set(edge.target_task_id, new Set());
    map.get(edge.source_task_id)!.add(edge.target_task_id);
    map.get(edge.target_task_id)!.add(edge.source_task_id);
  }
  return map;
}

/* ── Main Modal ────────────────────────────────────────────────────── */

export function UpstreamTopologyModal({ open, onClose, pipelineId }: UpstreamTopologyModalProps) {
  const [activeDagId, setActiveDagId] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);

  const dagRunId = useRunSelectorStore((s) => s.selectedDagRunId);
  const { data, isLoading } = useUpstreamTopology(pipelineId, activeDagId, open, dagRunId);
  const setSelectedPipelineId = usePipelineStore((s) => s.setSelectedPipelineId);

  const { containerRef, edgePaths, setNodeRef } = useEdgeDrawing(open, data?.edges);

  // The resolved DAG from the response (backend defaults to first DAG when activeDagId is null)
  const displayDagId = activeDagId ?? data?.dag_id ?? null;

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setActiveDagId(null);
      setHoveredNode(null);
      setExportOpen(false);
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

  // Close export dropdown when clicking outside
  useEffect(() => {
    if (!exportOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) {
        setExportOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [exportOpen]);

  const handleExport = useCallback(
    (format: "svg" | "png" | "html") => {
      setExportOpen(false);
      // Capture the full topology container (HTML nodes + SVG edges)
      const el = containerRef.current;
      if (!el) return;
      const name = data?.pipeline_task_id ?? "topology";
      switch (format) {
        case "svg":
          downloadAsSVG(el, name);
          break;
        case "png":
          downloadAsPNG(el, name);
          break;
        case "html":
          downloadAsInteractiveHTML(el, name);
          break;
      }
    },
    [containerRef, data],
  );

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

  // Pre-build adjacency map once when data changes — O(E) build, O(1) lookups
  const adjacencyMap = useMemo(() => {
    if (!data) return new Map<string, Set<string>>();
    return buildAdjacencyMap(data.edges);
  }, [data]);

  // Pre-compute highlight/dim state per node using adjacency map
  const nodeRenderState = useMemo(() => {
    if (!data) return new Map<string, { isHighlighted: boolean; isDimmed: boolean }>();
    const map = new Map<string, { isHighlighted: boolean; isDimmed: boolean }>();
    for (const node of data.nodes) {
      const connected = hoveredNode !== null && (
        hoveredNode === node.task_id ||
        (adjacencyMap.get(hoveredNode)?.has(node.task_id) ?? false)
      );
      map.set(node.task_id, {
        isHighlighted: hoveredNode !== null && connected,
        isDimmed: hoveredNode !== null && !connected,
      });
    }
    return map;
  }, [data, hoveredNode, adjacencyMap]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/85 backdrop-blur-md animate-in fade-in duration-200" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-[92vw] h-[88vh] bg-surface-modal border border-border rounded-2xl shadow-2xl shadow-black/60 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">

        {/* ── Header ──────────────────────────────────────────────── */}
        <div className="px-6 py-3.5 border-b border-border bg-surface-modal-header flex items-center gap-4 shrink-0">
          {/* Icon + Title */}
          <div className="size-8 bg-indigo-500/10 border border-indigo-500/20 rounded-lg flex items-center justify-center shrink-0">
            <GitFork className="size-4 text-indigo-400" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-foreground tracking-tight truncate">
              {data?.pipeline_task_id?.replace(/_/g, " ") ?? "Loading..."}
            </h2>
            <p className="text-[10px] text-text-faint font-mono mt-0.5">
              Upstream Dependency Graph
            </p>
          </div>

          {/* DAG selector tabs */}
          {dagIds.length > 1 && (
            <>
              <div className="w-px h-5 bg-hover-bg-strong mx-1" />
              <div className="flex bg-hover-bg rounded-lg p-0.5 border border-border">
                {dagIds.map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setActiveDagId(id)}
                    className={`px-3 py-1.5 text-[10px] font-mono rounded-md transition-all duration-200 ${
                      displayDagId === id
                        ? "bg-hover-bg-strong text-foreground shadow-sm"
                        : "text-text-muted hover:text-text-primary"
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
              <div className="w-px h-5 bg-hover-bg-strong mx-1" />
              <span className="text-[10px] font-mono text-text-muted px-2 py-1 rounded bg-hover-bg border border-border">
                {dagIds[0].replace(/_/g, " ")}
              </span>
            </>
          )}

          <div className="flex-1" />

          {/* Stats pills */}
          {data && (
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[9px] font-mono text-text-faint">
                {etlNodes.length} task{etlNodes.length !== 1 ? "s" : ""}
                {bouncerNodes.length > 0 && (<span className="text-text-faint"> + {bouncerNodes.length} bouncer{bouncerNodes.length !== 1 ? "s" : ""}</span>)}
                <span className="text-text-faint ml-1">{maxDepth + 1} layer{maxDepth !== 0 ? "s" : ""}</span>
              </span>
              <div className="w-px h-3 bg-hover-bg-strong" />
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

          {/* Export */}
          {data && data.nodes.length > 0 && (
            <div ref={exportRef} className="relative">
              <button
                onClick={() => setExportOpen((o) => !o)}
                className="p-1.5 text-text-faint hover:text-foreground hover:bg-hover-bg rounded-lg transition-all border border-transparent hover:border-border"
                title="Export topology"
              >
                <Download className="size-4" />
              </button>
              {exportOpen && (
                <div className="absolute right-0 top-full mt-1 w-44 py-1 rounded-lg border border-border bg-zinc-900 shadow-xl shadow-black/50 z-50">
                  <button
                    onClick={() => handleExport("svg")}
                    className="w-full px-3 py-1.5 text-left text-xs text-text-primary hover:bg-hover-bg-strong hover:text-foreground transition-colors"
                  >
                    Export SVG
                  </button>
                  <button
                    onClick={() => handleExport("png")}
                    className="w-full px-3 py-1.5 text-left text-xs text-text-primary hover:bg-hover-bg-strong hover:text-foreground transition-colors"
                  >
                    Export PNG
                  </button>
                  <button
                    onClick={() => handleExport("html")}
                    className="w-full px-3 py-1.5 text-left text-xs text-text-primary hover:bg-hover-bg-strong hover:text-foreground transition-colors"
                  >
                    Export Interactive HTML
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Close */}
          <button onClick={onClose} className="p-1.5 text-text-faint hover:text-foreground hover:bg-hover-bg rounded-lg transition-all border border-transparent hover:border-border">
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
                <span className="text-[10px] font-mono text-text-faint">Loading topology...</span>
              </div>
            </div>
          ) : !data || data.nodes.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="flex flex-col items-center gap-2">
                <GitFork className="size-5 text-text-faint" />
                <span className="text-[11px] text-text-faint font-mono">No upstream dependencies</span>
              </div>
            </div>
          ) : (
            <div className="relative inline-flex items-stretch min-w-full min-h-full p-8">
              {/* SVG edge overlay */}
              <TopologySvgEdges edgePaths={edgePaths} hoveredNode={hoveredNode} />

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
                          : "border-border bg-hover-bg"
                    }`}>
                      {/* Column header */}
                      <div className="flex items-center justify-center gap-2 mb-3">
                        {isBouncerLayer && <Radio className="w-3 h-3 text-teal-400/50" />}
                        <span className={`text-[9px] font-mono uppercase tracking-[0.15em] ${
                          isCurrent ? "text-indigo-400/60" : isBouncerLayer ? "text-teal-400/50" : "text-text-faint"
                        }`}>
                          {isCurrent ? "Current" : isBouncerLayer ? "Bouncers" : hasBouncers ? `Layer ${depth} + Bouncers` : `Layer ${depth}`}
                        </span>
                        <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded-full ${
                          isCurrent ? "text-indigo-400/40 bg-indigo-500/8" : isBouncerLayer ? "text-teal-500/30 bg-teal-500/5" : "text-text-faint bg-hover-bg"
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
            <div className="sticky bottom-3 left-3 z-10 inline-flex items-center gap-4 px-3 py-1.5 bg-black/50 backdrop-blur-sm rounded-lg border border-border ml-3 mb-3">
              <div className="flex items-center gap-1.5">
                <svg width="20" height="2" className="shrink-0"><line x1="0" y1="1" x2="20" y2="1" stroke="rgba(251,146,60,0.4)" strokeWidth="1.5" /></svg>
                <Lock className="w-2.5 h-2.5 text-orange-400/50" />
                <span className="text-[8px] font-mono text-text-muted">needs</span>
              </div>
              <div className="flex items-center gap-1.5">
                <svg width="20" height="2" className="shrink-0"><line x1="0" y1="1" x2="20" y2="1" stroke="rgba(56,189,248,0.3)" strokeWidth="1" strokeDasharray="4 3" /></svg>
                <Sparkles className="w-2.5 h-2.5 text-sky-400/50" />
                <span className="text-[8px] font-mono text-text-muted">prefers</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Radio className="w-2.5 h-2.5 text-teal-400/50" />
                <span className="text-[8px] font-mono text-text-muted">bouncer</span>
              </div>
              <div className="w-px h-3 bg-hover-bg-strong" />
              {Object.entries(STATUS_CONFIG).filter(([k]) => k !== "unknown").map(([key, cfg]) => (
                <div key={key} className="flex items-center gap-1">
                  <span className={`inline-block w-1.5 h-1.5 rounded-full ${cfg.dot.replace(" animate-pulse", "")}`} />
                  <span className="text-[7px] font-mono text-text-faint">{cfg.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

