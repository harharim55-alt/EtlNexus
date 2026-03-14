import { Columns3 } from "lucide-react";
import { parseProjectColumns } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function ProjectFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { columns, expressions } = parseProjectColumns(detail);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Columns3 className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
        <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
          Output Columns
          <span className="ml-1.5 text-slate-600">
            ({columns.length + expressions.length})
          </span>
        </span>
      </div>
      {columns.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {columns.map((col) => (
            <span
              key={col}
              className="text-[11px] font-mono text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 rounded-md px-2 py-0.5"
            >
              {col}
            </span>
          ))}
        </div>
      )}
      {expressions.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-600 mb-1.5">
            Expressions
          </div>
          <div className="space-y-1">
            {expressions.map((expr, i) => (
              <div
                key={i}
                className="text-[11px] font-mono text-violet-300/80 bg-violet-500/5 border border-violet-500/10 rounded-md px-2.5 py-1 break-all"
              >
                {expr}
              </div>
            ))}
          </div>
        </div>
      )}
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
