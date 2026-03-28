import { Lock, Sparkles } from "lucide-react";
import { TaskNode, FlowArrow, SectionLabel, TaskGroupLabel } from "./LineageNodes";
import { NeedsPrefDagGroup } from "./LineageSections";
import { groupByDag, groupByTaskGroup } from "./lineage-utils";
import type { TopologyTask } from "@/types/topology";

interface DependencySectionProps {
  needs: TopologyTask[];
  prefers: TopologyTask[];
  onTaskClick: (pipelineId: string) => void;
}

/**
 * Renders the needs/prefers dependency column in the LineageTopology view,
 * optionally grouped by DAG when multiple DAGs are present.
 */
export function DependencySection({ needs, prefers, onTaskClick }: DependencySectionProps) {
  const needsByDag = groupByDag(needs);
  const prefersByDag = groupByDag(prefers);
  const npDagIds = [
    ...new Set([
      ...Object.keys(needsByDag),
      ...Object.keys(prefersByDag),
    ]),
  ].sort();
  const isSingleGroup = npDagIds.length === 1;
  const totalNP = needs.length + prefers.length;

  return (
    <>
      <div className="flex-1 min-w-0 max-w-[240px] self-center">
        <span className="text-[9px] font-mono uppercase tracking-[0.15em] text-text-faint mb-2 block text-center">
          Dependencies
          <span className="text-text-faint ml-1.5">
            ({totalNP})
          </span>
        </span>

        {isSingleGroup ? (
          <div className="flex flex-col gap-1">
            {needs.length > 0 && (
              <div>
                <SectionLabel
                  label="Needs"
                  icon={<Lock className="w-2.5 h-2.5 text-orange-400/60" />}
                  accentColor="text-orange-400/60"
                />
                <div className="flex flex-col gap-1.5">
                  {(() => {
                    const { grouped, hasGroups } = groupByTaskGroup(needs);
                    if (!hasGroups) {
                      return needs.map((t) => (
                        <TaskNode
                          key={t.task_id}
                          task={t}
                          onClick={() =>
                            t.pipeline_id && onTaskClick(t.pipeline_id)
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
                              t.pipeline_id && onTaskClick(t.pipeline_id)
                            }
                          />
                        ))}
                      </div>
                    ));
                  })()}
                </div>
              </div>
            )}
            {prefers.length > 0 && (
              <div>
                <SectionLabel
                  label="Prefers"
                  icon={<Sparkles className="w-2.5 h-2.5 text-sky-400/60" />}
                  accentColor="text-sky-400/60"
                />
                <div className="flex flex-col gap-1.5">
                  {(() => {
                    const { grouped, hasGroups } = groupByTaskGroup(prefers);
                    if (!hasGroups) {
                      return prefers.map((t) => (
                        <TaskNode
                          key={t.task_id}
                          task={t}
                          onClick={() =>
                            t.pipeline_id && onTaskClick(t.pipeline_id)
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
                              t.pipeline_id && onTaskClick(t.pipeline_id)
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
                onTaskClick={onTaskClick}
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
}
