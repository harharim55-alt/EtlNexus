import { useState, useEffect, useCallback, useRef } from "react";
import type { TabType } from "@/lib/constants";

interface SpotlightConnectorProps {
  target: TabType;
  panelRef: React.RefObject<HTMLDivElement | null>;
}

/**
 * Draws an animated dashed SVG line from the onboarding panel
 * to the sidebar spotlight target.
 */
export function SpotlightConnector({ target, panelRef }: SpotlightConnectorProps) {
  const [line, setLine] = useState<{ x1: number; y1: number; x2: number; y2: number } | null>(null);
  const rafRef = useRef<number>(0);

  const updateLine = useCallback(() => {
    const navEl = document.querySelector(`[data-nav-id="${target}"]`);
    const panelEl = panelRef.current;
    if (!navEl || !panelEl) {
      setLine(null);
      return;
    }

    const navRect = navEl.getBoundingClientRect();
    const panelRect = panelEl.getBoundingClientRect();

    // Target: right edge of sidebar icon, vertically centered
    const x2 = navRect.right + 4;
    const y2 = navRect.top + navRect.height / 2;

    // Source: left edge of panel, vertically centered
    const x1 = panelRect.left;
    const y1 = panelRect.top + panelRect.height / 2;

    setLine({ x1, y1, x2, y2 });
  }, [target, panelRef]);

  useEffect(() => {
    // Delay first measurement to let panel position transition settle
    const timer = setTimeout(updateLine, 550);

    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(updateLine);
    });
    observer.observe(document.body);

    window.addEventListener("resize", updateLine);
    return () => {
      clearTimeout(timer);
      cancelAnimationFrame(rafRef.current);
      observer.disconnect();
      window.removeEventListener("resize", updateLine);
    };
  }, [updateLine]);

  if (!line) return null;

  return (
    <svg
      className="fixed inset-0 z-[58] pointer-events-none"
      style={{ width: "100vw", height: "100vh" }}
    >
      <line
        x1={line.x2}
        y1={line.y2}
        x2={line.x1}
        y2={line.y1}
        stroke="rgba(99, 102, 241, 0.25)"
        strokeWidth="1.5"
        strokeDasharray="6 8"
        style={{ animation: "dash 1.5s linear infinite" }}
      />
      {/* Source dot (panel side) */}
      <circle cx={line.x1} cy={line.y1} r="3" fill="rgba(99, 102, 241, 0.3)" />
      {/* Target dot (sidebar side) */}
      <circle cx={line.x2} cy={line.y2} r="3" fill="rgba(99, 102, 241, 0.5)" />
    </svg>
  );
}
