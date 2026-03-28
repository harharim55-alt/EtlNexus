import { Table2 } from "lucide-react";
import { parseScanDetail } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

const FORMAT_STYLES: Record<string, string> = {
  parquet: "text-sky-300 bg-sky-500/10 border-sky-500/20",
  csv: "text-orange-300 bg-orange-500/10 border-orange-500/20",
  json: "text-green-300 bg-green-500/10 border-green-500/20",
  orc: "text-purple-300 bg-purple-500/10 border-purple-500/20",
  text: "text-text-primary bg-slate-500/10 border-slate-500/20",
};

export function ScanFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { table, namespace, columns, filters, format, location } =
    parseScanDetail(detail);
  const fmtStyle =
    FORMAT_STYLES[format.toLowerCase()] ||
    "text-text-secondary bg-hover-bg border-border-prominent";

  return (
    <div className="space-y-4">
      {/* Table name + namespace + format badge */}
      <div className="flex items-center gap-2.5 flex-wrap">
        <Table2 className="w-4 h-4 text-blue-400 shrink-0" />
        <span className="text-sm font-semibold text-blue-300 font-mono">
          {table}
        </span>
        {namespace && (
          <span className="text-[9px] font-mono uppercase tracking-wider text-text-muted bg-hover-bg px-1.5 py-0.5 rounded">
            {namespace}
          </span>
        )}
        {format && (
          <span
            className={`text-[9px] font-mono uppercase tracking-wider font-bold border rounded-md px-1.5 py-0.5 ${fmtStyle}`}
          >
            {format}
          </span>
        )}
      </div>

      {/* Location path */}
      {location && (
        <div
          className="text-[11px] font-mono text-text-muted truncate px-3 py-1.5 bg-surface-inset rounded-lg border border-border"
          title={location}
        >
          {location}
        </div>
      )}

      {/* Columns */}
      {columns.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-text-muted mb-2">
            Columns
            <span className="ml-1.5 text-text-faint">({columns.length})</span>
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
          <div className="text-[10px] font-mono uppercase tracking-widest text-text-muted mb-2">
            Pushed Filters
            <span className="ml-1.5 text-text-faint">({filters.length})</span>
          </div>
          <div className="space-y-1">
            {filters.map((f, i) => (
              <div
                key={i}
                className="flex items-start gap-2 px-3 py-1.5 bg-surface-inset rounded-lg border border-border"
              >
                <span className="text-[9px] font-mono text-text-faint mt-0.5 shrink-0">
                  {i + 1}
                </span>
                <span className="text-[11px] font-mono text-text-primary break-all">
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
