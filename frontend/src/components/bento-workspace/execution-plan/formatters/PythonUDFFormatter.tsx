import { FileCode } from "lucide-react";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function PythonUDFFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  // Parse pipe-separated: "pandas udf | func1, func2" or "apply (pandas) | group by col1, col2"
  const sections = detail.split("|").map((s) => s.trim());
  const kind = sections[0] || "python";
  const extra = sections.slice(1).join(" | ");

  const isPandas = detail.includes("pandas");

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5 flex-wrap">
        <FileCode className="w-4 h-4 text-yellow-400 shrink-0" />
        <span className="text-sm font-semibold text-yellow-300 font-mono">
          {kind}
        </span>
        <span
          className={`text-[9px] font-mono font-bold uppercase tracking-wider rounded-md px-1.5 py-0.5 border ${
            isPandas
              ? "text-green-300 bg-green-500/10 border-green-500/20"
              : "text-yellow-300 bg-yellow-500/10 border-yellow-500/20"
          }`}
        >
          {isPandas ? "PANDAS" : "PYTHON"}
        </span>
      </div>

      {extra && (
        <div className="text-[11px] font-mono text-slate-300 px-3 py-2 bg-black/20 rounded-lg border border-white/[0.04]">
          {extra}
        </div>
      )}

      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
