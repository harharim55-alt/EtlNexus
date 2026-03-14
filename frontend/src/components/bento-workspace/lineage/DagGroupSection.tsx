import { BouncerNode, FlowArrow } from "./LineageNodes";
import { BouncerDagGroup } from "./LineageSections";
import { groupBouncersByDag } from "./lineage-utils";
import type { TopologyBouncer } from "@/types/topology";

interface DagGroupSectionProps {
  bouncers: TopologyBouncer[];
  onBouncerClick: (name: string) => void;
}

/**
 * Renders the bouncer column (leftmost) in the LineageTopology view,
 * optionally grouped by DAG when multiple DAGs are present.
 */
export function DagGroupSection({ bouncers, onBouncerClick }: DagGroupSectionProps) {
  const bouncersByDag = groupBouncersByDag(bouncers);
  const bouncerDagIds = Object.keys(bouncersByDag).sort();
  const isSingleGroup = bouncerDagIds.length === 1;

  return (
    <>
      <div className="flex-1 min-w-0 max-w-[200px] self-center">
        <span className="text-[9px] font-mono uppercase tracking-[0.15em] text-teal-400/50 mb-2 block text-center">
          Bouncers
          <span className="text-teal-500/30 ml-1.5">
            ({bouncers.length})
          </span>
        </span>

        {isSingleGroup ? (
          <div className="flex flex-col gap-1.5">
            {bouncers.map((s) => (
              <BouncerNode
                key={s.bouncer_name}
                bouncer={s}
                onClick={() => onBouncerClick(s.bouncer_name)}
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
                onBouncerClick={onBouncerClick}
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
}
