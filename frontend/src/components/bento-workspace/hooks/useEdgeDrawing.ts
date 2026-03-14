import { useRef, useState, useCallback, useEffect } from "react";

export interface EdgePath {
  d: string;
  type: string;
  sourceId: string;
  targetId: string;
  sx: number;
  sy: number;
  tx: number;
  ty: number;
}

interface EdgeData {
  source_task_id: string;
  target_task_id: string;
  edge_type: string;
}

/**
 * Manages SVG edge drawing between nodes in a scrollable container.
 * Extracts the edge calculation and lifecycle logic from UpstreamTopologyModal.
 */
export function useEdgeDrawing(open: boolean, edges: EdgeData[] | undefined) {
  const containerRef = useRef<HTMLDivElement>(null);
  const nodeRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const [edgePaths, setEdgePaths] = useState<EdgePath[]>([]);

  const drawEdges = useCallback(() => {
    if (!edges || !containerRef.current) return;
    const containerRect = containerRef.current.getBoundingClientRect();
    const scrollLeft = containerRef.current.scrollLeft;
    const scrollTop = containerRef.current.scrollTop;
    const paths: EdgePath[] = [];

    for (const edge of edges) {
      const sourceEl = nodeRefs.current.get(edge.source_task_id);
      const targetEl = nodeRefs.current.get(edge.target_task_id);
      if (!sourceEl || !targetEl) continue;

      const sr = sourceEl.getBoundingClientRect();
      const tr = targetEl.getBoundingClientRect();

      const sx = sr.right - containerRect.left + scrollLeft;
      const sy = sr.top + sr.height / 2 - containerRect.top + scrollTop;
      const tx = tr.left - containerRect.left + scrollLeft;
      const ty = tr.top + tr.height / 2 - containerRect.top + scrollTop;

      const dx = Math.max((tx - sx) * 0.4, 20);
      const d = `M${sx},${sy} C${sx + dx},${sy} ${tx - dx},${ty} ${tx},${ty}`;
      paths.push({ d, type: edge.edge_type, sourceId: edge.source_task_id, targetId: edge.target_task_id, sx, sy, tx, ty });
    }

    setEdgePaths(paths);
  }, [edges]);

  // Draw edges after layout settles (double-rAF)
  useEffect(() => {
    if (!open || !edges) return;
    const raf = requestAnimationFrame(() => { requestAnimationFrame(drawEdges); });
    return () => cancelAnimationFrame(raf);
  }, [open, edges, drawEdges]);

  // Redraw on window resize
  useEffect(() => {
    if (!open) return;
    window.addEventListener("resize", drawEdges);
    return () => window.removeEventListener("resize", drawEdges);
  }, [open, drawEdges]);

  // Redraw on container scroll
  useEffect(() => {
    if (!open || !containerRef.current) return;
    const el = containerRef.current;
    el.addEventListener("scroll", drawEdges);
    return () => el.removeEventListener("scroll", drawEdges);
  }, [open, drawEdges]);

  const setNodeRef = useCallback((taskId: string, el: HTMLDivElement | null) => {
    if (el) nodeRefs.current.set(taskId, el);
    else nodeRefs.current.delete(taskId);
  }, []);

  // Reset when modal closes
  useEffect(() => {
    if (!open) {
      setEdgePaths([]);
    }
  }, [open]);

  return { containerRef, edgePaths, setNodeRef };
}
