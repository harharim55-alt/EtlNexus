import { Filter as FilterIcon } from "lucide-react";
import { parseFilterPredicates } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function FilterFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const predicates = parseFilterPredicates(detail);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <FilterIcon className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
        <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
          Predicates
          <span className="ml-1.5 text-slate-600">({predicates.length})</span>
        </span>
      </div>
      <div className="space-y-1.5">
        {predicates.map((pred, i) => (
          <div
            key={i}
            className="flex items-start gap-2 text-xs font-mono"
          >
            <span className="text-indigo-500/60 select-none shrink-0 w-4 text-right">
              {i + 1}
            </span>
            <span className="text-slate-300 leading-relaxed break-all">
              {pred.split(/(AND|OR|>=|<=|!=|<>|=|>|<|notnull|isnotnull)/gi).map((seg, j) => {
                const upper = seg.toUpperCase();
                if (upper === "AND" || upper === "OR") {
                  return (
                    <span key={j} className="text-amber-400 font-semibold">
                      {seg}
                    </span>
                  );
                }
                if ([">=", "<=", "!=", "<>", "=", ">", "<"].includes(seg)) {
                  return (
                    <span key={j} className="text-cyan-400">
                      {seg}
                    </span>
                  );
                }
                if (
                  seg.toLowerCase() === "notnull" ||
                  seg.toLowerCase() === "isnotnull"
                ) {
                  return (
                    <span key={j} className="text-violet-400">
                      {seg}
                    </span>
                  );
                }
                return <span key={j}>{seg}</span>;
              })}
            </span>
          </div>
        ))}
      </div>
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
