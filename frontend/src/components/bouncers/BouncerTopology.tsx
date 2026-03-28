import { useState, useRef, useEffect, useCallback } from "react";
import { ChevronRight, Radio, Workflow } from "lucide-react";
import { useBouncerTopology } from "@/hooks/use-bouncers";
import { useBouncerStore } from "@/stores/bouncer-store";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useNavigationStore } from "@/stores/navigation-store";
import { Skeleton } from "@/components/ui/skeleton";
import { getStatusStyle } from "@/lib/status-config";
import { stripDummy } from "@/lib/format";
import { groupByDag } from "@/components/bento-workspace/lineage/lineage-utils";
import type { BouncerTopologyNode } from "@/types/bouncer";

function FlowArrow() {
  return (
    <div className="flex items-center justify-center w-10 shrink-0">
      <svg width="32" height="16" viewBox="0 0 32 16" className="text-teal-500/40">
        <line
          x1="0" y1="8" x2="24" y2="8"
          stroke="currentColor"
          strokeWidth="1"
          strokeDasharray="4 3"
          className="animate-[dash_1.5s_linear_infinite]"
        />
        <polyline
          points="20,4 26,8 20,12"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        />
      </svg>
    </div>
  );
}

function EtlNode({
  node,
  onClick,
}: {
  node: BouncerTopologyNode;
  onClick?: () => void;
}) {
  const cfg = getStatusStyle(node.status);
  const displayName = stripDummy(node.pipeline_name ?? node.task_id).replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/_/g, " ");
  const isClickable = !!node.pipeline_id;

  return (
    <button
      type="button"
      onClick={isClickable ? onClick : undefined}
      disabled={!isClickable}
      className={`
        group/node flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg border text-left transition-all duration-150
        bg-[#0f0f12] border-border hover:border-border-prominent hover:bg-hover-bg
        ${isClickable ? "cursor-pointer" : "cursor-default"}
      `}
    >
      <span
        className={`inline-block w-2 h-2 rounded-full shrink-0 ${cfg.dot} ${cfg.glow}`}
      />
      <div className="min-w-0 flex-1">
        <span className="text-[11px] font-medium block truncate text-text-primary group-hover/node:text-text-primary">
          {displayName}
        </span>
        <span className="text-[9px] font-mono text-text-faint block truncate">
          {node.task_id}
        </span>
      </div>
      <span
        className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${cfg.text} ${cfg.bg}`}
      >
        {cfg.label.toLowerCase()}
      </span>
    </button>
  );
}

function statusSummary(nodes: BouncerTopologyNode[]) {
  const counts: Record<string, number> = {};
  for (const n of nodes) {
    const s = n.status || "unknown";
    counts[s] = (counts[s] || 0) + 1;
  }
  return counts;
}

function DagGroup({
  dagId,
  nodes,
  onNodeClick,
  defaultOpen,
}: {
  dagId: string;
  nodes: BouncerTopologyNode[];
  onNodeClick: (id: string) => void;
  defaultOpen: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState<number | undefined>(undefined);

  const measure = useCallback(() => {
    if (contentRef.current) {
      setContentHeight(contentRef.current.scrollHeight);
    }
  }, []);

  useEffect(() => {
    measure();
  }, [nodes.length, measure]);

  const summary = statusSummary(nodes);
  const hasFailure = (summary.failed ?? 0) > 0;

  return (
    <div className="rounded-lg border border-border bg-hover-bg overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="flex items-center gap-2 w-full px-2.5 py-2 text-left hover:bg-hover-bg transition-colors cursor-pointer"
      >
        <ChevronRight
          className={`w-3 h-3 text-text-muted shrink-0 transition-transform duration-200 ${isOpen ? "rotate-90" : ""}`}
        />
        <span className="text-[10px] font-mono text-text-secondary truncate flex-1">
          {dagId.replace(/_/g, " ")}
        </span>

        <div className="flex items-center gap-1 shrink-0">
          {Object.entries(summary).map(([status, count]) => {
            const scfg = getStatusStyle(status);
            return (
              <span
                key={status}
                className={`flex items-center gap-1 text-[8px] font-mono px-1.5 py-0.5 rounded ${scfg.text} ${scfg.bg}`}
              >
                <span className={`inline-block w-1.5 h-1.5 rounded-full ${scfg.dot}`} />
                {count}
              </span>
            );
          })}
        </div>

        <span
          className={`text-[9px] font-mono tabular-nums shrink-0 ${hasFailure ? "text-rose-400/60" : "text-text-faint"}`}
        >
          {nodes.length}
        </span>
      </button>

      <div
        style={{
          height: isOpen ? contentHeight ?? "auto" : 0,
          opacity: isOpen ? 1 : 0,
        }}
        className="transition-all duration-200 ease-out overflow-hidden"
      >
        <div ref={contentRef} className="px-2 pb-2 flex flex-col gap-1.5">
          {nodes.map((n) => (
            <EtlNode
              key={n.task_id}
              node={n}
              onClick={() => n.pipeline_id && onNodeClick(n.pipeline_id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export function BouncerTopology() {
  const selectedBouncers = useBouncerStore((s) => s.selectedBouncers);
  const topologyMode = useBouncerStore((s) => s.topologyMode);
  const setTopologyMode = useBouncerStore((s) => s.setTopologyMode);
  const setSelectedPipelineId = usePipelineStore((s) => s.setSelectedPipelineId);
  const setActiveTab = useNavigationStore((s) => s.setActiveTab);

  const { data, isLoading } = useBouncerTopology(selectedBouncers, topologyMode);

  const navigateToEtl = (pipelineId: string) => {
    setSelectedPipelineId(pipelineId);
    setActiveTab("catalog");
  };

  if (selectedBouncers.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center px-6 py-12">
        <div className="bg-teal-500/5 p-4 rounded-2xl border border-teal-500/10 mb-4">
          <Radio className="w-8 h-8 text-teal-500/30" />
        </div>
        <p className="text-sm text-text-secondary mb-1">No bouncers selected</p>
        <p className="text-[11px] text-text-faint max-w-[240px]">
          Select one or more bouncers from the list to view downstream ETL dependencies
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex-1 p-4 space-y-3">
        <Skeleton className="h-5 w-48 bg-hover-bg" />
        <Skeleton className="h-32 bg-hover-bg rounded-xl" />
        <Skeleton className="h-24 bg-hover-bg rounded-xl" />
      </div>
    );
  }

  const dagGroups = groupByDag(data?.downstream_etls ?? []);
  const dagIds = Object.keys(dagGroups);

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Header with mode toggle */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <Workflow className="w-3.5 h-3.5 text-teal-400/60" />
          <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted">
            Downstream ETLs
          </span>
          <span className="text-[10px] font-mono text-teal-400/50">
            {data?.total_etl_count ?? 0}
          </span>
        </div>

        {selectedBouncers.length >= 2 && (
          <div className="flex items-center gap-1 bg-hover-bg rounded-lg p-0.5 border border-border">
            <button
              type="button"
              onClick={() => setTopologyMode("union")}
              className={`text-[9px] font-mono px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                topologyMode === "union"
                  ? "text-teal-300 bg-teal-500/15"
                  : "text-text-muted hover:text-text-secondary"
              }`}
            >
              Union
            </button>
            <button
              type="button"
              onClick={() => setTopologyMode("intersection")}
              className={`text-[9px] font-mono px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                topologyMode === "intersection"
                  ? "text-teal-300 bg-teal-500/15"
                  : "text-text-muted hover:text-text-secondary"
              }`}
            >
              Intersect
            </button>
          </div>
        )}
      </div>

      {/* Topology content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
        {/* Selected bouncers row */}
        <div className="mb-4">
          <span className="text-[9px] font-mono uppercase tracking-widest text-text-faint mb-2 block">
            Selected Bouncers
          </span>
          <div className="flex flex-wrap gap-1.5">
            {selectedBouncers.map((name) => (
              <span
                key={name}
                className="inline-flex items-center gap-1.5 text-[10px] font-mono px-2.5 py-1 rounded-full bg-teal-500/10 text-teal-300 border border-teal-500/20"
              >
                <Radio className="w-2.5 h-2.5" />
                {name.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>

        {/* Flow arrow */}
        <div className="flex justify-center mb-4">
          <FlowArrow />
        </div>

        {/* Downstream ETLs grouped by DAG */}
        {dagIds.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-[11px] text-text-faint font-mono">
              No downstream ETLs found
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {dagIds.map((dagId) => (
              <DagGroup
                key={dagId}
                dagId={dagId}
                nodes={dagGroups[dagId]}
                onNodeClick={navigateToEtl}
                defaultOpen={dagIds.length <= 4}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
