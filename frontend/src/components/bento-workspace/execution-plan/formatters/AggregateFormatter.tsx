import { parseAggregateDetail } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function AggregateFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { groupBy, functions } = parseAggregateDetail(detail);

  return (
    <div className="space-y-4">
      {groupBy.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2">
            Group By
          </div>
          <div className="flex flex-wrap gap-1.5">
            {groupBy.map((col) => (
              <span
                key={col}
                className="text-[11px] font-mono text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 rounded-md px-2 py-0.5"
              >
                {col}
              </span>
            ))}
          </div>
        </div>
      )}
      {functions.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2">
            Aggregations
          </div>
          <div className="flex flex-wrap gap-1.5">
            {functions.map((fn) => (
              <span
                key={fn}
                className="text-[11px] font-mono text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-md px-2 py-0.5"
              >
                {fn}()
              </span>
            ))}
          </div>
        </div>
      )}
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
