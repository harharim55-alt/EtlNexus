import { ChevronUp, ChevronDown } from "lucide-react";
import { parseWindowDetail } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function WindowFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { partitionBy, orderBy, functions } = parseWindowDetail(detail);

  return (
    <div className="space-y-4">
      {/* Window Functions */}
      {functions.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2">
            Window Functions
          </div>
          <div className="flex flex-wrap gap-1.5">
            {functions.map((fn) => (
              <span
                key={fn}
                className="text-[11px] font-mono text-violet-300 bg-violet-500/10 border border-violet-500/20 rounded-md px-2 py-0.5"
              >
                {fn}()
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Partition By */}
      {partitionBy.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2">
            Partition By
          </div>
          <div className="flex flex-wrap gap-1.5">
            {partitionBy.map((col) => (
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

      {/* Order By */}
      {orderBy.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2">
            Order By
          </div>
          <div className="space-y-1.5">
            {orderBy.map((k, i) => (
              <div
                key={i}
                className="flex items-center gap-2 px-3 py-2 bg-black/20 rounded-lg border border-white/[0.04]"
              >
                {k.direction === "ASC" ? (
                  <ChevronUp className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                )}
                <span className="text-xs font-mono text-slate-300">
                  {k.column}
                </span>
                <span className="text-[9px] font-mono text-slate-600 ml-auto">
                  {k.direction}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
