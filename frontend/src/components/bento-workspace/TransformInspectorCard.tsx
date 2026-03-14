import { useState } from "react";
import { GitMerge } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useExecutionPlan } from "@/hooks/use-execution-plan";
import { formatDuration } from "@/lib/format";
import type { ExecutionPlanNode } from "@/types/execution-plan";
import { NodeDetailModal } from "./execution-plan/PlanFormatters";
import { TreeNode, treeStyles } from "./execution-plan/PlanTree";
import { RunPicker } from "./execution-plan/PlanRunSelector";

interface TransformInspectorCardProps {
  pipelineId: string;
}

export function TransformInspectorCard({
  pipelineId,
}: TransformInspectorCardProps) {
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>();
  const { data, isLoading } = useExecutionPlan(pipelineId, selectedRunId);
  const [expandedNode, setExpandedNode] = useState<ExecutionPlanNode | null>(
    null,
  );

  if (isLoading) {
    return (
      <div className="col-span-12 bg-[#18181b] border border-white/[0.06] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/[0.06] flex items-center gap-3">
          <Skeleton className="h-4 w-4 bg-white/5 rounded" />
          <Skeleton className="h-3 w-40 bg-white/5" />
        </div>
        <div className="p-10 flex justify-center">
          <Skeleton className="h-48 w-96 bg-white/5 rounded-xl" />
        </div>
      </div>
    );
  }

  if (!data?.execution_plan) return null;

  return (
    <div className="col-span-12 bg-[#18181b] border border-white/[0.06] rounded-2xl overflow-hidden">
      <style>{treeStyles}</style>

      {/* Header */}
      <div className="px-6 py-4 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <GitMerge className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-mono uppercase tracking-widest text-slate-300">
            Logical Execution DAG
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-3 text-[11px] font-mono text-slate-500">
            <span>{data.dag_id}</span>
            {data.duration_seconds != null && (
              <>
                <span className="text-slate-700">|</span>
                <span>{formatDuration(data.duration_seconds)}</span>
              </>
            )}
          </div>
          <RunPicker
            pipelineId={pipelineId}
            currentRunId={data.dag_run_id}
            onSelect={setSelectedRunId}
          />
        </div>
      </div>

      {/* Canvas body */}
      <div className="relative overflow-x-auto" style={{ maxHeight: 500 }}>
        <div
          className="absolute inset-0 opacity-[0.08] pointer-events-none"
          style={{
            backgroundImage:
              "radial-gradient(#94a3b8 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
        />
        <div className="relative min-w-max flex justify-center p-10">
          <div className="tree-container">
            <ul>
              <TreeNode
                node={data.execution_plan}
                onExpand={setExpandedNode}
              />
            </ul>
          </div>
        </div>
      </div>

      {/* Node detail modal */}
      {expandedNode && (
        <NodeDetailModal
          node={expandedNode}
          onClose={() => setExpandedNode(null)}
        />
      )}
    </div>
  );
}
