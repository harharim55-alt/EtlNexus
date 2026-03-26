import { useState, useCallback } from "react";
import { GitFork, Layers, Network } from "lucide-react";
import { UpstreamTopologyModal } from "./UpstreamTopologyModal";
import { useLineage } from "@/hooks/use-lineage";
import { useTopology } from "@/hooks/use-topology";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useRunSelectorStore } from "@/stores/run-selector-store";
import { useNavigationStore } from "@/stores/navigation-store";
import { useBouncerStore } from "@/stores/bouncer-store";
import { Skeleton } from "@/components/ui/skeleton";
import type { TopologyTask } from "@/types/topology";
import { TaskNode, FlowArrow, TaskGroupLabel } from "./lineage/LineageNodes";
import { DownstreamDagGroup } from "./lineage/LineageSections";
import { groupByDag, groupByTaskGroup } from "./lineage/lineage-utils";
import { DagGroupSection } from "./lineage/DagGroupSection";
import { DependencySection } from "./lineage/DependencySection";

interface LineageTopologyProps {
  pipelineId: string;
  fullWidth?: boolean;
}

export function LineageTopology({ pipelineId, fullWidth }: LineageTopologyProps) {
  const [upstreamOpen, setUpstreamOpen] = useState(false);
  const selectedDagId = usePipelineStore((s) => s.selectedDagId);
  const setSelectedDagId = usePipelineStore((s) => s.setSelectedDagId);
  const dagRunId = useRunSelectorStore((s) => s.selectedDagRunId);
  const { data: topology, isLoading: topoLoading } = useTopology(pipelineId, selectedDagId, dagRunId);
  const { data: lineage, isLoading: lineageLoading } = useLineage(pipelineId);
  const setSelectedPipelineId = usePipelineStore(
    (s) => s.setSelectedPipelineId,
  );
  const setActiveTab = useNavigationStore((s) => s.setActiveTab);
  const clearBouncers = useBouncerStore((s) => s.clearBouncers);
  const toggleBouncer = useBouncerStore((s) => s.toggleBouncer);

  const handleBouncerClick = useCallback(
    (bouncerName: string) => {
      clearBouncers();
      toggleBouncer(bouncerName);
      setActiveTab("bouncers");
    },
    [clearBouncers, toggleBouncer, setActiveTab],
  );

  const isLoading = topoLoading || lineageLoading;

  const colSpan = fullWidth ? "col-span-12" : "col-span-12 lg:col-span-8";

  if (isLoading) {
    return (
      <div className={`${colSpan} bg-[#18181b] border border-white/5 rounded-2xl p-6`}>
        <Skeleton className="h-5 w-40 mb-6 bg-white/5" />
        <Skeleton className="h-32 bg-white/5 rounded-xl" />
      </div>
    );
  }

  const destinationTables = lineage?.destination_tables ?? [];
  const hasTopology =
    topology &&
    ((topology.upstream_bouncers?.length ?? 0) > 0 ||
      topology.upstream_needs.length > 0 ||
      topology.upstream_prefers.length > 0 ||
      topology.downstream.length > 0);

  const currentTask: TopologyTask = {
    task_id: topology?.pipeline_task_id ?? "",
    pipeline_name: null,
    pipeline_id: pipelineId,
    status: topology?.pipeline_status ?? "unknown",
    dag_id: topology?.dag_ids?.[0] ?? "",
    task_group_id: null,
  };

  const hasBouncers = (topology?.upstream_bouncers?.length ?? 0) > 0;
  const hasNeedsPrefers =
    (topology?.upstream_needs.length ?? 0) > 0 ||
    (topology?.upstream_prefers.length ?? 0) > 0;

  return (
    <div className={`${colSpan} bg-[#18181b] border border-white/5 rounded-2xl p-6 relative overflow-hidden group`}>
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

      <div className="flex items-center justify-between mb-5">
        <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
          <Network className="w-3.5 h-3.5" /> Pipeline Topology
        </h3>
        <div className="flex items-center gap-1.5">
          {topology?.dag_ids && topology.dag_ids.length > 0 && (
            <>
              {topology.dag_ids.length > 1 && (
                <button
                  type="button"
                  onClick={() => setSelectedDagId(null)}
                  className={`text-[9px] font-mono px-2 py-1 rounded border transition-all cursor-pointer ${
                    selectedDagId === null
                      ? "text-indigo-400 bg-indigo-500/10 border-indigo-500/30"
                      : "text-slate-500 bg-white/[0.03] border-white/5 hover:border-white/15"
                  }`}
                >
                  all
                </button>
              )}
              {topology.dag_ids.map((dagId) => (
                <button
                  type="button"
                  key={dagId}
                  onClick={() => setSelectedDagId(dagId)}
                  className={`text-[9px] font-mono px-2 py-1 rounded border transition-all cursor-pointer ${
                    selectedDagId === dagId
                      ? "text-indigo-400 bg-indigo-500/10 border-indigo-500/30"
                      : "text-slate-500 bg-white/[0.03] border-white/5 hover:border-white/15"
                  }`}
                >
                  {dagId}
                </button>
              ))}
              <div className="w-px h-4 bg-white/[0.08] mx-0.5" />
            </>
          )}
          <button
            type="button"
            onClick={() => setUpstreamOpen(true)}
            className="text-[9px] font-mono px-2 py-1 rounded border transition-all cursor-pointer text-slate-500 bg-white/[0.03] border-white/5 hover:border-indigo-500/30 hover:text-indigo-400 hover:bg-indigo-500/10 flex items-center gap-1.5"
          >
            <GitFork className="w-3 h-3" />
            Full Upstream
          </button>
        </div>
      </div>

      {hasTopology ? (
        <div className="flex items-start justify-center gap-0">
          {/* Bouncers column (leftmost) — grouped by DAG */}
          {hasBouncers && (
            <DagGroupSection
              bouncers={topology!.upstream_bouncers}
              onBouncerClick={handleBouncerClick}
            />
          )}

          {/* Needs / Prefers column — grouped by DAG */}
          {hasNeedsPrefers && (
            <DependencySection
              needs={topology!.upstream_needs}
              prefers={topology!.upstream_prefers}
              onTaskClick={setSelectedPipelineId}
            />
          )}

          {/* Current pipeline (center) */}
          <div className="flex-1 min-w-0 max-w-[240px] self-center">
            <span className="text-[9px] font-mono uppercase tracking-[0.15em] text-slate-600 mb-2 block text-center">
              Current
            </span>
            <TaskNode task={currentTask} isCurrent />
          </div>

          {/* Downstream column — grouped by DAG */}
          {topology!.downstream.length > 0 && (() => {
            const dagGroups = groupByDag(topology!.downstream);
            const dagIds = Object.keys(dagGroups);
            const isSingleGroup = dagIds.length === 1;

            return (
              <>
                <div className="flex items-center self-center pt-3">
                  <FlowArrow />
                </div>
                <div className="flex-1 min-w-0 max-w-[260px] self-center">
                  <span className="text-[9px] font-mono uppercase tracking-[0.15em] text-slate-600 mb-2 block text-center">
                    Downstream
                    <span className="text-slate-700 ml-1.5">
                      ({topology!.downstream.length})
                    </span>
                  </span>

                  {isSingleGroup ? (
                    /* Single DAG — task group labels if available, flat otherwise */
                    (() => {
                      const { grouped, hasGroups } = groupByTaskGroup(
                        topology!.downstream,
                      );
                      if (!hasGroups) {
                        return (
                          <div className="flex flex-col gap-1.5">
                            {topology!.downstream.map((t) => (
                              <TaskNode
                                key={t.task_id}
                                task={t}
                                onClick={() =>
                                  t.pipeline_id &&
                                  setSelectedPipelineId(t.pipeline_id)
                                }
                              />
                            ))}
                          </div>
                        );
                      }
                      return (
                        <div className="flex flex-col gap-1">
                          {Object.entries(grouped).map(([gId, gTasks]) => (
                            <div key={gId}>
                              {gId !== "_ungrouped" && (
                                <TaskGroupLabel groupId={gId} />
                              )}
                              <div className="flex flex-col gap-1.5">
                                {gTasks.map((t) => (
                                  <TaskNode
                                    key={t.task_id}
                                    task={t}
                                    onClick={() =>
                                      t.pipeline_id &&
                                      setSelectedPipelineId(t.pipeline_id)
                                    }
                                  />
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      );
                    })()
                  ) : (
                    /* Multiple DAGs — collapsible subgroups */
                    <div className="flex flex-col gap-1">
                      {dagIds.map((dagId) => (
                        <DownstreamDagGroup
                          key={dagId}
                          dagId={dagId}
                          tasks={dagGroups[dagId]}
                          onTaskClick={setSelectedPipelineId}
                          defaultOpen={dagIds.length <= 3}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </>
            );
          })()}
        </div>
      ) : (
        /* Fallback: no topology data */
        <div className="flex flex-col items-center w-full max-w-xl mx-auto mt-2">
          {destinationTables.length > 0 ? (
            <div className="w-full">
              <div className="flex items-center gap-1.5 mb-3">
                <Layers className="w-3.5 h-3.5 text-indigo-400/50" />
                <span className="text-[9px] font-mono uppercase tracking-widest text-indigo-400/50">
                  Writes To
                </span>
                <span className="text-[9px] font-mono text-slate-600">
                  ({destinationTables.length})
                </span>
              </div>
              <div className="flex flex-wrap gap-1">
                {destinationTables.map((t) => (
                  <span
                    key={t}
                    title={t}
                    className="text-[9px] bg-indigo-500/5 px-2 py-1 rounded text-indigo-400/50 font-mono border border-indigo-500/10"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <span className="text-[10px] text-slate-600 font-mono">
              No table output
            </span>
          )}
        </div>
      )}

      {/* Writes To footer */}
      {hasTopology && destinationTables.length > 0 && (
        <div className="mt-5 pt-4 border-t border-white/5">
          <div className="flex items-center gap-1.5 mb-2">
            <Layers className="w-3 h-3 text-indigo-400/50" />
            <span className="text-[9px] font-mono uppercase tracking-widest text-indigo-400/50">
              Writes To
            </span>
            <span className="text-[9px] font-mono text-slate-600">
              ({destinationTables.length})
            </span>
          </div>
          <div className="flex flex-wrap gap-1">
            {destinationTables.map((t) => (
              <span
                key={t}
                title={t}
                className="text-[9px] bg-indigo-500/5 px-2 py-1 rounded text-indigo-400/50 font-mono border border-indigo-500/10"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      <UpstreamTopologyModal
        open={upstreamOpen}
        onClose={() => setUpstreamOpen(false)}
        pipelineId={pipelineId}
      />
    </div>
  );
}
