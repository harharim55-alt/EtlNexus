import { Zap } from "lucide-react";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function CacheFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  // Reuse scan parser — InMemoryTableScan has similar structure: "cached\ncolumns: col1, col2\nfilters: ..."
  const lines = detail.split("\n").map((l) => l.trim());
  const columns: string[] = [];
  const filters: string[] = [];

  for (const line of lines) {
    if (line.startsWith("columns:")) {
      columns.push(
        ...line
          .replace("columns:", "")
          .trim()
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      );
    } else if (line.startsWith("filters:")) {
      filters.push(
        ...line
          .replace("filters:", "")
          .trim()
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      );
    }
  }

  // Fallback: try parsing cached [col1, col2] format
  if (columns.length === 0) {
    const m = detail.match(/cached\s*\[(.+)\]/);
    if (m) {
      columns.push(
        ...m[1]
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      );
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <Zap className="w-4 h-4 text-yellow-400 shrink-0" />
        <span className="text-sm font-semibold text-yellow-300 font-mono">
          Cached Scan
        </span>
        <span className="text-[10px] font-mono font-bold text-yellow-300 bg-yellow-500/10 border border-yellow-500/20 rounded-md px-2 py-0.5">
          IN-MEMORY
        </span>
      </div>

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
                className="text-[11px] font-mono text-yellow-300 bg-yellow-500/10 border border-yellow-500/20 rounded-md px-2 py-0.5"
              >
                {col}
              </span>
            ))}
          </div>
        </div>
      )}

      {filters.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-text-muted mb-2">
            Filters
          </div>
          <div className="space-y-1">
            {filters.map((f, i) => (
              <div
                key={i}
                className="text-[11px] font-mono text-text-primary px-3 py-1.5 bg-surface-inset rounded-lg border border-border"
              >
                {f}
              </div>
            ))}
          </div>
        </div>
      )}

      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
