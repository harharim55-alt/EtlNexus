import type { EdgePath } from "./hooks/useEdgeDrawing";

/* ── Props ─────────────────────────────────────────────────────────── */

interface TopologySvgEdgesProps {
  edgePaths: EdgePath[];
  hoveredNode: string | null;
}

/* ── Component ─────────────────────────────────────────────────────── */

const SVG_OVERLAY_STYLE: React.CSSProperties = {
  width: "100%",
  height: "100%",
  overflow: "visible",
};

export function TopologySvgEdges({ edgePaths, hoveredNode }: TopologySvgEdgesProps) {
  return (
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
  );
}
