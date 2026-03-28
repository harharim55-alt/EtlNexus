import { useState, useRef, useEffect, useCallback } from "react";
import { ChevronRight, Lock, Sparkles } from "lucide-react";
import type { TopologyTask, TopologyBouncer } from "@/types/topology";
import { BouncerNode, SectionLabel } from "./LineageNodes";
import { CollapsibleLineageGroup, TaskList } from "./CollapsibleLineageGroup";

export function BouncerDagGroup({
  dagId,
  bouncers,
  onBouncerClick,
  defaultOpen,
}: {
  dagId: string;
  bouncers: TopologyBouncer[];
  onBouncerClick: (name: string) => void;
  defaultOpen: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState<number | undefined>(
    undefined,
  );

  const measure = useCallback(() => {
    if (contentRef.current) {
      setContentHeight(contentRef.current.scrollHeight);
    }
  }, []);

  useEffect(() => {
    measure();
  }, [bouncers.length, measure]);

  return (
    <div className="rounded-lg border border-teal-500/[0.08] bg-teal-500/[0.01] overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="flex items-center gap-2 w-full px-2.5 py-2 text-left hover:bg-teal-500/[0.03] transition-colors cursor-pointer"
      >
        <ChevronRight
          className={`w-3 h-3 text-teal-500/40 shrink-0 transition-transform duration-200 ${isOpen ? "rotate-90" : ""}`}
        />
        <span className="text-[10px] font-mono text-text-secondary truncate flex-1">
          {dagId.replace(/_/g, " ")}
        </span>
        <span className="text-[9px] font-mono tabular-nums shrink-0 text-teal-400/50">
          {bouncers.length}
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
          {bouncers.map((s) => (
            <BouncerNode
              key={s.bouncer_name}
              bouncer={s}
              onClick={() => onBouncerClick(s.bouncer_name)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export function NeedsPrefDagGroup({
  dagId,
  needs,
  prefers,
  onTaskClick,
  defaultOpen,
}: {
  dagId: string;
  needs: TopologyTask[];
  prefers: TopologyTask[];
  onTaskClick: (id: string) => void;
  defaultOpen: boolean;
}) {
  const allTasks = [...needs, ...prefers];
  const hasBothSections = needs.length > 0 && prefers.length > 0;

  return (
    <CollapsibleLineageGroup
      dagId={dagId}
      tasks={allTasks}
      onTaskClick={onTaskClick}
      defaultOpen={defaultOpen}
    >
      {needs.length > 0 && (
        <div>
          {hasBothSections && (
            <SectionLabel
              label="Needs"
              icon={<Lock className="w-2.5 h-2.5 text-orange-400/60" />}
              accentColor="text-orange-400/60"
            />
          )}
          <TaskList tasks={needs} onTaskClick={onTaskClick} />
        </div>
      )}

      {prefers.length > 0 && (
        <div>
          {hasBothSections && (
            <SectionLabel
              label="Prefers"
              icon={<Sparkles className="w-2.5 h-2.5 text-sky-400/60" />}
              accentColor="text-sky-400/60"
            />
          )}
          <TaskList tasks={prefers} onTaskClick={onTaskClick} />
        </div>
      )}
    </CollapsibleLineageGroup>
  );
}

export function DownstreamDagGroup({
  dagId,
  tasks,
  onTaskClick,
  defaultOpen,
}: {
  dagId: string;
  tasks: TopologyTask[];
  onTaskClick: (id: string) => void;
  defaultOpen: boolean;
}) {
  return (
    <CollapsibleLineageGroup
      dagId={dagId}
      tasks={tasks}
      onTaskClick={onTaskClick}
      defaultOpen={defaultOpen}
    />
  );
}
