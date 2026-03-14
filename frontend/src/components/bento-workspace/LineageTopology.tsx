import { useState, useCallback } from "react";
import { GitFork, Layers, Lock, Network, Sparkles } from "lucide-react";
import { UpstreamTopologyModal } from "./UpstreamTopologyModal";
import { useLineage } from "@/hooks/use-lineage";
import { useTopology } from "@/hooks/use-topology";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useNavigationStore } from "@/stores/navigation-store";
import { useBouncerStore } from "@/stores/bouncer-store";
import { Skeleton } from "@/components/ui/skeleton";
import type { TopologyTask } from "@/types/topology";
import { TaskNode, BouncerNode, FlowArrow, SectionLabel, TaskGroupLabel } from "./lineage/LineageNodes";
import { BouncerDagGroup, NeedsPrefDagGroup, DownstreamDagGroup } from "./lineage/LineageSections";
import { groupBouncersByDag, groupByDag, groupByTaskGroup } from "./lineage/lineage-utils";

interface LineageTopologyProps {
  pipelineId: string;
}

export function LineageTopology({ pipelineId }: LineageTopologyProps) {
  const [upstreamOpen, setUpstreamOpen] = useState(false);
  const selectedDagId = usePipelineStore((s) => s.selectedDagId);
  const setSelectedDagId = usePipelineStore((s) => s.setSelectedDagId);
  const { data: topology, isLoading: topoLoading } = useTopology(pipelineId, selectedDagId);
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

  if (isLoading) {
    return (
      <div className="col-span-12 lg:col-span-8 bg-[#18181b] border border-white/5 rounded-2xl p-6">
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
    <div className="col-span-12 lg:col-span-8 bg-[#18181b] border border-white/5 rounded-2xl p-6 relative overflow-hidden group">
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
          {hasBouncers && (() => {
            const bouncersByDag = groupBouncersByDag(topology!.upstream_bouncers);
            const bouncerDagIds = Object.keys(bouncersByDag).sort();
            const isSingleGroup = bouncerDagIds.length === 1;

            return (
              <>
                <div className="flex-1 min-w-0 max-w-[200px] self-center">
                  <span className="text-[9px] font-mono uppercase tracking-[0.15em] text-teal-400/50 mb-2 block text-center">
                    Bouncers
                    <span className="text-teal-500/30 ml-1.5">
                      ({topology!.upstream_bouncers.length})
                    </span>
                  </span>

                  {isSingleGroup ? (
                    <div className="flex flex-col gap-1.5">
                      {topology!.upstream_bouncers.map((s) => (
                        <BouncerNode
                          key={s.sensor_name}
                          bouncer={s}
                          onClick={() => handleBouncerClick(s.sensor_name)}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col gap-1">
                      {bouncerDagIds.map((dagId) => (
                        <BouncerDagGroup
                          key={dagId}
                          dagId={dagId}
                          bouncers={bouncersByDag[dagId]}
                          onBouncerClick={handleBouncerClick}
                          defaultOpen={bouncerDagIds.length <= 3}
                        />
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex items-center self-center pt-3">
                  <FlowArrow />
                </div>
              </>
            );
          })()}

          {/* Needs / Prefers column — grouped by DAG */}
          {hasNeedsPrefers && (() => {
            const needsByDag = groupByDag(topology!.upstream_needs);
            const prefersByDag = groupByDag(topology!.upstream_prefers);
            const npDagIds = [
              ...new Set([
                ...Object.keys(needsByDag),
                ...Object.keys(prefersByDag),
              ]),
            ].sort();
            const isSingleGroup = npDagIds.length === 1;
            const totalNP =
              topology!.upstream_needs.length +
              topology!.upstream_prefers.length;

            return (
              <>
                <div className="flex-1 min-w-0 max-w-[240px] self-center">
                  <span className="text-[9px] font-mono uppercase tracking-[0.15em] text-slate-600 mb-2 block text-center">
                    Dependencies
                    <span className="text-slate-700 ml-1.5">
                      ({totalNP})
                    </span>
                  </span>

                  {isSingleGroup ? (
                    <div className="flex flex-col gap-1">
                      {topology!.upstream_needs.length > 0 && (
                        <div>
                          <SectionLabel
                            label="Needs"
                            icon={<Lock className="w-2.5 h-2.5 text-orange-400/60" />}
                            accentColor="text-orange-400/60"
                          />
                          <div className="flex flex-col gap-1.5">
                            {(() => {
                              const { grouped, hasGroups } = groupByTaskGroup(topology!.upstream_needs);
                              if (!hasGroups) {
                                return topology!.upstream_needs.map((t) => (
                                  <TaskNode
                                    key={t.task_id}
                                    task={t}
                                    onClick={() =>
                                      t.pipeline_id && setSelectedPipelineId(t.pipeline_id)
                                    }
                                  />
                                ));
                              }
                              return Object.entries(grouped).map(([gId, gTasks]) => (
                                <div key={gId}>
                                  {gId !== "_ungrouped" && <TaskGroupLabel groupId={gId} />}
                                  {gTasks.map((t) => (
                                    <TaskNode
                                      key={t.task_id}
                                      task={t}
                                      onClick={() =>
                                        t.pipeline_id && setSelectedPipelineId(t.pipeline_id)
                                      }
                                    />
                                  ))}
                                </div>
                              ));
                            })()}
                          </div>
                        </div>
                      )}
                      {topology!.upstream_prefers.length > 0 && (
                        <div>
                          <SectionLabel
                            label="Prefers"
                            icon={<Sparkles className="w-2.5 h-2.5 text-sky-400/60" />}
                            accentColor="text-sky-400/60"
                          />
                          <div className="flex flex-col gap-1.5">
                            {(() => {
                              const { grouped, hasGroups } = groupByTaskGroup(topology!.upstream_prefers);
                              if (!hasGroups) {
                                return topology!.upstream_prefers.map((t) => (
                                  <TaskNode
                                    key={t.task_id}
                                    task={t}
                                    onClick={() =>
                                      t.pipeline_id && setSelectedPipelineId(t.pipeline_id)
                                    }
                                  />
                                ));
                              }
                              return Object.entries(grouped).map(([gId, gTasks]) => (
                                <div key={gId}>
                                  {gId !== "_ungrouped" && <TaskGroupLabel groupId={gId} />}
                                  {gTasks.map((t) => (
                                    <TaskNode
                                      key={t.task_id}
                                      task={t}
                                      onClick={() =>
                                        t.pipeline_id && setSelectedPipelineId(t.pipeline_id)
                                      }
                                    />
                                  ))}
                                </div>
                              ));
                            })()}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex flex-col gap-1">
                      {npDagIds.map((dagId) => (
                        <NeedsPrefDagGroup
                          key={dagId}
                          dagId={dagId}
                          needs={needsByDag[dagId] ?? []}
                          prefers={prefersByDag[dagId] ?? []}
                          onTaskClick={setSelectedPipelineId}
                          defaultOpen={npDagIds.length <= 3}
                        />
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex items-center self-center pt-3">
                  <FlowArrow />
                </div>
              </>
            );
          })()}

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
                    className="text-[9px] bg-indigo-500/5 px-2 py-1 rounded text-indigo-400/50 font-mono border border-indigo-500/10 truncate max-w-[160px]"
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
                className="text-[9px] bg-indigo-500/5 px-2 py-1 rounded text-indigo-400/50 font-mono border border-indigo-500/10 truncate max-w-[160px]"
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
