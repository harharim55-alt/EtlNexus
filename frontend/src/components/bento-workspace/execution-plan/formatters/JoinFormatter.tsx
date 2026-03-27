import { ArrowRight } from "lucide-react";
import { parseJoinDetail } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function JoinFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { joinType, leftKey, rightKey, strategy, buildSide, condition } =
    parseJoinDetail(detail, node.name);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-300 bg-amber-500/15 border border-amber-500/25 rounded-lg px-2.5 py-1">
          {joinType}
        </span>
        {strategy && (
          <span className="text-[9px] font-mono text-slate-400 bg-white/5 border border-white/10 rounded-md px-1.5 py-0.5">
            {strategy}
          </span>
        )}
        {buildSide && (
          <span className="text-[9px] font-mono text-slate-500 bg-white/[0.03] rounded px-1.5 py-0.5">
            build {buildSide}
          </span>
        )}
      </div>

      {/* Equi-join keys */}
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

      {/* Non-equi join condition */}
      {condition && !leftKey && !rightKey && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-600 mb-1.5">
            Condition
          </div>
          <div className="text-[11px] font-mono text-slate-300 bg-black/30 p-3 rounded-lg break-all leading-relaxed">
            {condition}
          </div>
        </div>
      )}

      {/* No condition at all (CartesianProduct) */}
      {!leftKey && !rightKey && !condition && joinType === "CROSS" && (
        <div className="text-[11px] font-mono text-slate-500 italic px-4 py-2">
          No join condition (cartesian product)
        </div>
      )}

      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
