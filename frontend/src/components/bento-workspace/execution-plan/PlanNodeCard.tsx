import { Maximize2 } from "lucide-react";
import { NODE_STYLES, TIME_KEYS, HIDDEN_KEYS } from "./plan-constants";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function NodeCard({
  node,
  onExpand,
}: {
  node: ExecutionPlanNode;
  onExpand: (node: ExecutionPlanNode) => void;
}) {
  const style = NODE_STYLES[node.type] ?? NODE_STYLES.transform;
  const Icon = style.icon;
  const entries = Object.entries(node.metrics);
  const rows = node.metrics.rows;
  const timeEntry = entries.find(([k]) => TIME_KEYS.has(k));
  const rest = entries.filter(
    ([k]) => k !== "rows" && !TIME_KEYS.has(k) && !HIDDEN_KEYS.has(k),
  );
  const hasContent = node.detail || entries.length > 0;

  return (
    <div
      className={`group/card relative inline-flex flex-col gap-1.5 px-4 py-3 rounded-xl border ${style.bg} ${style.border} min-w-[170px] max-w-[260px]`}
    >
      {hasContent && (
        <button
          onClick={() => onExpand(node)}
          className="absolute top-2 right-2 p-1 rounded-md opacity-0 group-hover/card:opacity-100 transition-opacity text-slate-500 hover:text-slate-300 hover:bg-white/5"
          title="Expand details"
        >
          <Maximize2 className="w-3 h-3" />
        </button>
      )}
      <div className="flex items-center gap-2">
        <Icon className={`w-3.5 h-3.5 shrink-0 ${style.text}`} />
        <span className={`text-xs font-semibold truncate ${style.text}`}>
          {node.name}
        </span>
      </div>
      {node.detail && (
        <span
          className="text-[10px] font-mono text-slate-400 leading-tight line-clamp-2"
          title={node.detail}
        >
          {node.detail}
        </span>
      )}
      {entries.length > 0 && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-0.5 border-t border-white/5 pt-1.5">
          {timeEntry && (
            <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
              <span className="text-slate-600">⏱</span>
              {timeEntry[1]}
            </span>
          )}
          {rows && (
            <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
              <span className="text-slate-600">≣</span>
              {rows}
            </span>
          )}
          {rest.map(([key, val]) => (
            <span
              key={key}
              className="text-[9px] font-mono text-slate-500"
            >
              <span className="text-slate-600">{key}:</span>{" "}
              <span className="text-slate-400">{val}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
