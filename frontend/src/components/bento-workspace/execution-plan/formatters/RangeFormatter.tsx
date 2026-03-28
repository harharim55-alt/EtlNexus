import { Hash } from "lucide-react";
import { parseRangeDetail } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function RangeFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { start, end, step, partitions } = parseRangeDetail(detail);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <Hash className="w-4 h-4 text-blue-400 shrink-0" />
        <span className="text-sm font-semibold text-blue-300 font-mono">
          Range
        </span>
        {partitions && (
          <span className="text-[10px] font-mono text-text-muted bg-hover-bg px-1.5 py-0.5 rounded">
            {partitions} partitions
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-2">
        {start && (
          <div className="flex flex-col items-center px-3 py-2 bg-surface-inset rounded-lg border border-border">
            <span className="text-[10px] font-mono text-text-muted">start</span>
            <span className="text-sm font-mono font-semibold text-blue-300">
              {start}
            </span>
          </div>
        )}
        {end && (
          <div className="flex flex-col items-center px-3 py-2 bg-surface-inset rounded-lg border border-border">
            <span className="text-[10px] font-mono text-text-muted">end</span>
            <span className="text-sm font-mono font-semibold text-blue-300">
              {end}
            </span>
          </div>
        )}
        {step && (
          <div className="flex flex-col items-center px-3 py-2 bg-surface-inset rounded-lg border border-border">
            <span className="text-[10px] font-mono text-text-muted">step</span>
            <span className="text-sm font-mono font-semibold text-text-primary">
              {step}
            </span>
          </div>
        )}
      </div>

      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
