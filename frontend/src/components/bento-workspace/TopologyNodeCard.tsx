import { Radio } from "lucide-react";
import { getStatusStyle } from "@/lib/status-config";
import { stripDummy } from "@/lib/format";
import type { UpstreamNode } from "@/types/topology";

/* ── Edge type border colors ─────────────────────────────────────── */

const EDGE_BORDER: Record<string, string> = {
  needs: "border-l-orange-400/50",
  prefers: "border-l-sky-400/40",
  current: "border-l-indigo-400/60",
  bouncer: "border-l-teal-400/50",
  root: "border-l-slate-600/30",
};

/* ── NodeCard Props ───────────────────────────────────────────────── */

interface NodeCardProps {
  node: UpstreamNode;
  edgeType: "needs" | "prefers" | "current" | "bouncer" | "root";
  isHighlighted: boolean;
  isDimmed: boolean;
  onClick: () => void;
}

export function NodeCard({
  node,
  edgeType,
  isHighlighted,
  isDimmed,
  onClick,
}: NodeCardProps) {
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

/* ── BouncerNodeCard Props ────────────────────────────────────────── */

interface BouncerNodeCardProps {
  node: UpstreamNode;
  isHighlighted: boolean;
  isDimmed: boolean;
}

export function BouncerNodeCard({
  node,
  isHighlighted,
  isDimmed,
}: BouncerNodeCardProps) {
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
