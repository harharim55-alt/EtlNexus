import { useState, useRef, useEffect, useCallback } from "react";
import { ChevronRight, Lock, Sparkles } from "lucide-react";
import { getStatusStyle } from "@/lib/status-config";
import type { TopologyTask, TopologyBouncer } from "@/types/topology";
import { TaskNode, BouncerNode, SectionLabel, TaskGroupLabel } from "./LineageNodes";
import { groupByTaskGroup, statusSummary } from "./lineage-utils";

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
        <span className="text-[10px] font-mono text-slate-400 truncate flex-1">
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
              key={s.sensor_name}
              bouncer={s}
              onClick={() => onBouncerClick(s.sensor_name)}
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

  const totalCount = needs.length + prefers.length;

  useEffect(() => {
    measure();
  }, [totalCount, measure]);

  const allTasks = [...needs, ...prefers];
  const summary = statusSummary(allTasks);
  const hasFailure = (summary.failed ?? 0) > 0;

  return (
    <div className="rounded-lg border border-white/[0.04] bg-white/[0.01] overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="flex items-center gap-2 w-full px-2.5 py-2 text-left hover:bg-white/[0.02] transition-colors cursor-pointer"
      >
        <ChevronRight
          className={`w-3 h-3 text-slate-500 shrink-0 transition-transform duration-200 ${isOpen ? "rotate-90" : ""}`}
        />
        <span className="text-[10px] font-mono text-slate-400 truncate flex-1">
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
                <span
                  className={`inline-block w-1.5 h-1.5 rounded-full ${scfg.dot}`}
                />
                {count}
              </span>
            );
          })}
        </div>

        <span
          className={`text-[9px] font-mono tabular-nums shrink-0 ${hasFailure ? "text-rose-400/60" : "text-slate-600"}`}
        >
          {totalCount}
        </span>
      </button>

      <div
        style={{
          height: isOpen ? contentHeight ?? "auto" : 0,
          opacity: isOpen ? 1 : 0,
        }}
        className="transition-all duration-200 ease-out overflow-hidden"
      >
        <div ref={contentRef} className="px-2 pb-2 flex flex-col gap-1">
          {needs.length > 0 && (
            <div>
              {(needs.length > 0 && prefers.length > 0) && (
                <SectionLabel
                  label="Needs"
                  icon={<Lock className="w-2.5 h-2.5 text-orange-400/60" />}
                  accentColor="text-orange-400/60"
                />
              )}
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
                      {gId !== "_ungrouped" && (
                        <TaskGroupLabel groupId={gId} />
                      )}
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
              {(needs.length > 0 && prefers.length > 0) && (
                <SectionLabel
                  label="Prefers"
                  icon={<Sparkles className="w-2.5 h-2.5 text-sky-400/60" />}
                  accentColor="text-sky-400/60"
                />
              )}
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
                      {gId !== "_ungrouped" && (
                        <TaskGroupLabel groupId={gId} />
                      )}
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
      </div>
    </div>
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
  }, [tasks.length, measure]);

  const summary = statusSummary(tasks);
  const hasFailure = (summary.failed ?? 0) > 0;

  return (
    <div className="rounded-lg border border-white/[0.04] bg-white/[0.01] overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="flex items-center gap-2 w-full px-2.5 py-2 text-left hover:bg-white/[0.02] transition-colors cursor-pointer"
      >
        <ChevronRight
          className={`w-3 h-3 text-slate-500 shrink-0 transition-transform duration-200 ${isOpen ? "rotate-90" : ""}`}
        />
        <span className="text-[10px] font-mono text-slate-400 truncate flex-1">
          {dagId.replace(/_/g, " ")}
        </span>

        {/* Mini status pills */}
        <div className="flex items-center gap-1 shrink-0">
          {Object.entries(summary).map(([status, count]) => {
            const cfg = getStatusStyle(status);
            return (
              <span
                key={status}
                className={`flex items-center gap-1 text-[8px] font-mono px-1.5 py-0.5 rounded ${cfg.text} ${cfg.bg}`}
              >
                <span
                  className={`inline-block w-1.5 h-1.5 rounded-full ${cfg.dot}`}
                />
                {count}
              </span>
            );
          })}
        </div>

        <span
          className={`text-[9px] font-mono tabular-nums shrink-0 ${hasFailure ? "text-rose-400/60" : "text-slate-600"}`}
        >
          {tasks.length}
        </span>
      </button>

      <div
        style={{
          height: isOpen ? contentHeight ?? "auto" : 0,
          opacity: isOpen ? 1 : 0,
        }}
        className="transition-all duration-200 ease-out overflow-hidden"
      >
        <div ref={contentRef} className="px-2 pb-2 flex flex-col gap-1">
          {(() => {
            const { grouped, hasGroups } = groupByTaskGroup(tasks);
            if (!hasGroups) {
              return (
                <div className="flex flex-col gap-1.5">
                  {tasks.map((t) => (
                    <TaskNode
                      key={t.task_id}
                      task={t}
                      onClick={() =>
                        t.pipeline_id && onTaskClick(t.pipeline_id)
                      }
                    />
                  ))}
                </div>
              );
            }
            return Object.entries(grouped).map(([gId, gTasks]) => (
              <div key={gId}>
                {gId !== "_ungrouped" && <TaskGroupLabel groupId={gId} />}
                <div className="flex flex-col gap-1.5">
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
              </div>
            ));
          })()}
        </div>
      </div>
    </div>
  );
}
