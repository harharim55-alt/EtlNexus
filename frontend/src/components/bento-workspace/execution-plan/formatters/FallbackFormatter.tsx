import type { ExecutionPlanNode } from "@/types/execution-plan";

export function FallbackFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const entries = Object.entries(node.metrics);

  return (
    <div className="space-y-4">
      {detail && (
        <div className="text-xs font-mono text-text-primary bg-surface-inset p-3 rounded-lg break-all leading-relaxed whitespace-pre-wrap">
          {detail}
        </div>
      )}
      {entries.length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {entries.map(([key, val]) => (
            <div
              key={key}
              className="flex items-center justify-between bg-surface-inset px-3 py-2 rounded-lg"
            >
              <span className="text-[10px] font-mono text-text-muted">
                {key}
              </span>
              <span className="text-xs font-mono text-text-primary">{val}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
