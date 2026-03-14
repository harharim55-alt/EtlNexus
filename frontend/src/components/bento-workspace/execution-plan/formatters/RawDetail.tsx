import type { ExecutionPlanNode } from "@/types/execution-plan";

export function RawDetail({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const entries = Object.entries(node.metrics);

  return (
    <div className="space-y-4">
      {detail && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-1.5">
            Full Detail
          </div>
          <div className="text-xs font-mono text-slate-300 bg-black/30 p-3 rounded-lg break-all leading-relaxed whitespace-pre-wrap">
            {detail}
          </div>
        </div>
      )}
      {entries.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-1.5">
            Metrics
          </div>
          <div className="grid grid-cols-2 gap-2">
            {entries.map(([key, val]) => (
              <div
                key={key}
                className="flex items-center justify-between bg-black/30 px-3 py-2 rounded-lg"
              >
                <span className="text-[10px] font-mono text-slate-500">
                  {key}
                </span>
                <span className="text-xs font-mono text-slate-300">
                  {val}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
