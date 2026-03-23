import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Hook for toggling an "overview" (bird's-eye) mode on a scrollable tree canvas.
 *
 * Measures the tree content's natural size vs. the container's visible area
 * and calculates a scale factor to fit the entire tree inside.
 *
 * Returns a callback ref for the container, a regular ref for the tree wrapper,
 * and the overview state/toggle/scale.
 */
export function useOverview() {
  const [isOverview, setIsOverview] = useState(false);
  const [scale, setScale] = useState(1);
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const treeRef = useRef<HTMLDivElement>(null);

  const containerRef = useCallback(
    (node: HTMLDivElement | null) => setContainer(node),
    [],
  );

  // Recalculate scale when overview is toggled or container resizes
  useEffect(() => {
    if (!container || !treeRef.current) return;

    function recalc() {
      const tree = treeRef.current;
      if (!tree || !container) return;

      // Measure tree at natural size (scale=1)
      const prevTransform = tree.style.transform;
      tree.style.transform = "scale(1)";
      const treeW = tree.scrollWidth;
      const treeH = tree.scrollHeight;
      tree.style.transform = prevTransform;

      const containerW = container.clientWidth;
      const containerH = container.clientHeight;

      if (treeW === 0 || treeH === 0) return;

      const s = Math.min(containerW / treeW, containerH / treeH, 1);
      setScale(Math.max(s, 0.05));
    }

    if (isOverview) {
      // Double rAF to let layout settle
      requestAnimationFrame(() => requestAnimationFrame(recalc));
    }

    const ro = new ResizeObserver(() => {
      if (isOverview) recalc();
    });
    ro.observe(container);

    return () => ro.disconnect();
  }, [isOverview, container]);

  const toggleOverview = useCallback(() => setIsOverview((v) => !v), []);

  return { containerRef, treeRef, isOverview, toggleOverview, scale };
}
