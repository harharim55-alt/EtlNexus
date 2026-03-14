import { ArrowRight } from "lucide-react";
import { parseJoinDetail } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function JoinFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { joinType, leftKey, rightKey, strategy } = parseJoinDetail(
    detail,
    node.name,
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-300 bg-amber-500/15 border border-amber-500/25 rounded-lg px-2.5 py-1">
          {joinType}
        </span>
        {strategy && (
          <span className="text-[10px] font-mono text-slate-500">
            {strategy}
          </span>
        )}
      </div>
      {(leftKey || rightKey) && (
        <div className="flex items-center gap-3 px-4 py-3 bg-black/20 rounded-xl border border-white/[0.04]">
          <span className="text-xs font-mono text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-md px-2 py-0.5">
            {leftKey || "?"}
          </span>
          <ArrowRight className="w-4 h-4 text-slate-600 shrink-0" />
          <span className="text-xs font-mono text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-md px-2 py-0.5">
            {rightKey || leftKey || "?"}
          </span>
        </div>
      )}
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
