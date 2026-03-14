import { Shuffle } from "lucide-react";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function ExchangeFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <Shuffle className="w-4 h-4 text-amber-400 shrink-0" />
        <span className="text-sm font-mono text-amber-300">{detail}</span>
      </div>
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
