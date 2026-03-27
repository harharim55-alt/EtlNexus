import { Percent } from "lucide-react";
import { parseSampleDetail } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function SampleFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { fraction, withReplacement, seed } = parseSampleDetail(detail);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <Percent className="w-4 h-4 text-pink-400 shrink-0" />
        <span className="text-sm font-semibold text-pink-300 font-mono">
          Sample
        </span>
        {fraction && (
          <span className="text-[10px] font-mono font-bold text-pink-300 bg-pink-500/10 border border-pink-500/20 rounded-md px-2 py-0.5">
            {fraction}
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {withReplacement && (
          <div className="flex items-center gap-1.5 px-3 py-2 bg-black/20 rounded-lg border border-white/[0.04]">
            <span className="text-[10px] font-mono text-slate-500">mode</span>
            <span className="text-xs font-mono text-pink-300">
              with replacement
            </span>
          </div>
        )}
        {seed && (
          <div className="flex items-center gap-1.5 px-3 py-2 bg-black/20 rounded-lg border border-white/[0.04]">
            <span className="text-[10px] font-mono text-slate-500">seed</span>
            <span className="text-xs font-mono text-slate-300">{seed}</span>
          </div>
        )}
      </div>

      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
