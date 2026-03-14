import { ChevronUp, ChevronDown } from "lucide-react";
import { parseSortKeys } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function SortFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const keys = parseSortKeys(detail);

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        {keys.map((k, i) => (
          <div
            key={i}
            className="flex items-center gap-2 px-3 py-2 bg-black/20 rounded-lg border border-white/[0.04]"
          >
            {k.direction === "ASC" ? (
              <ChevronUp className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5 text-rose-400 shrink-0" />
            )}
            <span className="text-xs font-mono text-slate-300">{k.column}</span>
            <span className="text-[9px] font-mono text-slate-600 ml-auto">
              {k.direction}
            </span>
          </div>
        ))}
      </div>
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
