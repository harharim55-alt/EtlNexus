import { useState } from "react";
import { GitMerge, Maximize2, ScanEye } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useExecutionPlan } from "@/hooks/use-execution-plan";
import { formatDuration } from "@/lib/format";
import { useRunSelectorStore } from "@/stores/run-selector-store";
import type { ExecutionPlanNode } from "@/types/execution-plan";
import { NodeDetailModal } from "./execution-plan/PlanFormatters";
import { TreeNode, treeStyles } from "./execution-plan/PlanTree";
import { RunPicker } from "./execution-plan/PlanRunSelector";
import { usePannable } from "./execution-plan/usePannable";
import { useOverview } from "./execution-plan/useOverview";
import { ExecutionPlanModal } from "./ExecutionPlanModal";

interface TransformInspectorCardProps {
  pipelineId: string;
}

export function TransformInspectorCard({
  pipelineId,
}: TransformInspectorCardProps) {
  const globalRunId = useRunSelectorStore((s) => s.selectedDagRunId);
  const [localRunId, setLocalRunId] = useState<string | undefined>();
  // Global run selector takes precedence over local run picker
  const effectiveRunId = globalRunId ?? localRunId;
  const { data, isLoading } = useExecutionPlan(pipelineId, effectiveRunId);
  const [expandedNode, setExpandedNode] = useState<ExecutionPlanNode | null>(
    null,
  );
  const [fullscreenOpen, setFullscreenOpen] = useState(false);
  const panRef = usePannable<HTMLDivElement>();
  const { containerRef, treeRef, isOverview, toggleOverview, scale } =
    useOverview();

  if (isLoading) {
    return (
      <div className="col-span-12 bg-card border border-border rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-border flex items-center gap-3">
          <Skeleton className="h-4 w-4 bg-hover-bg rounded" />
          <Skeleton className="h-3 w-40 bg-hover-bg" />
        </div>
        <div className="p-10 flex justify-center">
          <Skeleton className="h-48 w-96 bg-hover-bg rounded-xl" />
        </div>
      </div>
    );
  }

  if (!data?.execution_plan) return null;

  return (
    <div className="col-span-12 bg-card border border-border rounded-2xl overflow-hidden">
      <style>{treeStyles}</style>

      {/* Header */}
      <div className="px-6 py-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <GitMerge className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-mono uppercase tracking-widest text-text-primary">
            Logical Execution DAG
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-3 text-[11px] font-mono text-text-muted">
            <span>{data.dag_id}</span>
            {data.duration_seconds != null && (
              <>
                <span className="text-text-faint">|</span>
                <span>{formatDuration(data.duration_seconds)}</span>
              </>
            )}
          </div>
          <RunPicker
            pipelineId={pipelineId}
            currentRunId={data.dag_run_id}
            onSelect={setLocalRunId}
          />
          <button
            type="button"
            onClick={toggleOverview}
            className={`text-[9px] font-mono px-2 py-1 rounded border transition-all cursor-pointer flex items-center gap-1.5 ${
              isOverview
                ? "text-indigo-400 bg-indigo-500/10 border-indigo-500/30"
                : "text-text-muted bg-hover-bg border-border hover:border-indigo-500/30 hover:text-indigo-400 hover:bg-indigo-500/10"
            }`}
          >
            <ScanEye className="w-3 h-3" />
            Overview
          </button>
          <button
            type="button"
            onClick={() => setFullscreenOpen(true)}
            className="text-[9px] font-mono px-2 py-1 rounded border transition-all cursor-pointer text-text-muted bg-hover-bg border-border hover:border-indigo-500/30 hover:text-indigo-400 hover:bg-indigo-500/10 flex items-center gap-1.5"
          >
            <Maximize2 className="w-3 h-3" />
            Full Plan
          </button>
        </div>
      </div>

      {/* Canvas body */}
      <div
        ref={(node) => {
          // Merge panRef (callback) and containerRef (callback)
          panRef(node);
          containerRef(node);
        }}
        className="relative overflow-auto custom-scrollbar"
        style={{ maxHeight: 500 }}
      >
        <div
          className="absolute inset-0 opacity-[0.08] pointer-events-none"
          style={{
            backgroundImage:
              "radial-gradient(var(--text-muted) 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
        />
        <div
          ref={treeRef}
          className="relative min-w-max flex justify-center p-10"
          style={
            isOverview
              ? {
                  transform: `scale(${scale})`,
                  transformOrigin: "center top",
                  minWidth: "unset",
                }
              : undefined
          }
        >
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

      {/* Fullscreen modal */}
      <ExecutionPlanModal
        open={fullscreenOpen}
        onClose={() => setFullscreenOpen(false)}
        data={data}
      />
    </div>
  );
}
