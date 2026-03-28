import { Columns3, ArrowRight } from "lucide-react";
import { parseProjectColumns } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function ProjectFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { passthrough, renamed, computed } = parseProjectColumns(detail);
  const total = passthrough.length + renamed.length + computed.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Columns3 className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
        <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted">
          Output Columns
          <span className="ml-1.5 text-text-faint">({total})</span>
        </span>
      </div>

      {/* Passthrough columns */}
      {passthrough.length > 0 && (
        <div>
          {(renamed.length > 0 || computed.length > 0) && (
            <div className="text-[10px] font-mono uppercase tracking-widest text-text-faint mb-1.5">
              Passthrough
              <span className="ml-1.5 text-text-faint">
                ({passthrough.length})
              </span>
            </div>
          )}
          <div className="flex flex-wrap gap-1.5">
            {passthrough.map((col) => (
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

      {/* Renamed columns */}
      {renamed.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-text-faint mb-1.5">
            Renamed
            <span className="ml-1.5 text-text-faint">({renamed.length})</span>
          </div>
          <div className="space-y-1">
            {renamed.map((r, i) => (
              <div
                key={i}
                className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/5 rounded-lg border border-amber-500/10"
              >
                <span className="text-[11px] font-mono text-text-secondary">
                  {r.from}
                </span>
                <ArrowRight className="w-3 h-3 text-amber-400 shrink-0" />
                <span className="text-[11px] font-mono text-amber-300 font-semibold">
                  {r.to}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Computed expressions */}
      {computed.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-text-faint mb-1.5">
            Computed
            <span className="ml-1.5 text-text-faint">({computed.length})</span>
          </div>
          <div className="space-y-1">
            {computed.map((c, i) => (
              <div
                key={i}
                className="text-[11px] font-mono text-violet-300/80 bg-violet-500/5 border border-violet-500/10 rounded-md px-2.5 py-1 break-all"
              >
                {c.alias ? (
                  <>
                    <span className="text-violet-300 font-semibold">
                      {c.alias}
                    </span>
                    <span className="text-text-faint mx-1">=</span>
                    <span className="text-text-secondary">{c.expression}</span>
                  </>
                ) : (
                  c.expression
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
