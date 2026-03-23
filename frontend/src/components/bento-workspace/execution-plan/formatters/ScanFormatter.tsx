import { Table2 } from "lucide-react";
import { parseScanDetail } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function ScanFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { table, namespace, columns, filters } = parseScanDetail(detail);

  return (
    <div className="space-y-4">
      {/* Table name + namespace */}
      <div className="flex items-center gap-2.5">
        <Table2 className="w-4 h-4 text-blue-400 shrink-0" />
        <span className="text-sm font-semibold text-blue-300 font-mono">
          {table}
        </span>
        {namespace && (
          <span className="text-[9px] font-mono uppercase tracking-wider text-slate-500 bg-white/5 px-1.5 py-0.5 rounded">
            {namespace}
          </span>
        )}
      </div>

      {/* Columns */}
      {columns.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2">
            Columns
            <span className="ml-1.5 text-slate-600">({columns.length})</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {columns.map((col) => (
              <span
                key={col}
                className="text-[11px] font-mono text-blue-300 bg-blue-500/10 border border-blue-500/20 rounded-md px-2 py-0.5"
              >
                {col}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      {filters.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2">
            Pushed Filters
            <span className="ml-1.5 text-slate-600">({filters.length})</span>
          </div>
          <div className="space-y-1">
            {filters.map((f, i) => (
              <div
                key={i}
                className="flex items-start gap-2 px-3 py-1.5 bg-black/20 rounded-lg border border-white/[0.04]"
              >
                <span className="text-[9px] font-mono text-slate-600 mt-0.5 shrink-0">
                  {i + 1}
                </span>
                <span className="text-[11px] font-mono text-slate-300 break-all">
                  {f
                    .replace(/\bIS NOT NULL\b/g, '<is_not_null>')
                    .replace(/\bIS NULL\b/g, '<is_null>')
                    .split(/(\b(?:AND|OR|NOT|>=|<=|>|<|=)\b|<is_not_null>|<is_null>)/g)
                    .map((part, j) => {
                      const restored = part
                        .replace('<is_not_null>', 'IS NOT NULL')
                        .replace('<is_null>', 'IS NULL');
                      if (/^(AND|OR|NOT|>=|<=|>|<|=|IS NOT NULL|IS NULL)$/.test(restored)) {
                        return (
                          <span key={j} className="text-amber-400 font-semibold">
                            {restored}
                          </span>
                        );
                      }
                      return restored;
                    })}
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
