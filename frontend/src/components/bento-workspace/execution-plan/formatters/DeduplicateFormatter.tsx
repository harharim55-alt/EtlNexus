import { CopyMinus } from "lucide-react";
import { parseDeduplicateDetail } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function DeduplicateFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { columns } = parseDeduplicateDetail(detail);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <CopyMinus className="w-4 h-4 text-teal-400 shrink-0" />
        <span className="text-sm font-semibold text-teal-300 font-mono">
          Deduplicate
        </span>
        {columns.length > 0 && (
          <span className="text-[10px] font-mono text-slate-500 bg-white/5 px-1.5 py-0.5 rounded">
            {columns.length} {columns.length === 1 ? "column" : "columns"}
          </span>
        )}
      </div>

      {columns.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2">
            Dedup Keys
          </div>
          <div className="flex flex-wrap gap-1.5">
            {columns.map((col) => (
              <span
                key={col}
                className="text-[11px] font-mono text-teal-300 bg-teal-500/10 border border-teal-500/20 rounded-md px-2 py-0.5"
              >
                {col}
              </span>
            ))}
          </div>
        </div>
      )}

      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
