import { Minus, CircleDot } from "lucide-react";
import { parseSetOpDetail } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function SetOperationFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { operation, isAll } = parseSetOpDetail(detail, node.name);
  const Icon = operation === "EXCEPT" ? Minus : CircleDot;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <Icon className="w-4 h-4 text-rose-400 shrink-0" />
        <span className="text-sm font-semibold text-rose-300 font-mono">
          {operation}
        </span>
        {isAll && (
          <span className="text-[10px] font-mono font-bold text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-md px-2 py-0.5">
            ALL
          </span>
        )}
        <span className="text-[10px] font-mono text-slate-500 bg-white/5 px-1.5 py-0.5 rounded">
          {node.children.length} branches
        </span>
      </div>
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
