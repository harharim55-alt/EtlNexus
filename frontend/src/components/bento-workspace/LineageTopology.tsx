import { useState, useRef, useEffect, useCallback } from "react";
import { ChevronRight, GitFork, Layers, Lock, Network, Radio, Sparkles } from "lucide-react";
import { UpstreamTopologyModal } from "./UpstreamTopologyModal";
import { useLineage } from "@/hooks/use-lineage";
import { useTopology } from "@/hooks/use-topology";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useNavigationStore } from "@/stores/navigation-store";
import { useBouncerStore } from "@/stores/bouncer-store";
import { Skeleton } from "@/components/ui/skeleton";
import { getStatusStyle } from "@/lib/status-config";
import type { TopologyTask, TopologyBouncer } from "@/types/topology";

interface LineageTopologyProps {
  pipelineId: string;
}

function StatusDot({ status }: { status: string }) {
  const cfg = getStatusStyle(status);
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full shrink-0 ${cfg.dot} ${cfg.glow}`}
      title={cfg.label}
    />
  );
}

function TaskNode({
  task,
  isCurrent,
  onClick,
}: {
  task: TopologyTask & { isCurrent?: boolean };
  isCurrent?: boolean;
  onClick?: () => void;
}) {
  const displayName = task.pipeline_name ?? task.task_id.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/_/g, " ");
  const isClickable = !isCurrent && !!task.pipeline_id;
  const cfg = getStatusStyle(task.status);

  return (
    <button
      type="button"
      onClick={isClickable ? onClick : undefined}
      disabled={!isClickable}
      className={`
        group/node flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg border text-left transition-all duration-150
        ${
          isCurrent
            ? "bg-indigo-500/10 border-indigo-500/30 shadow-[0_0_20px_rgba(99,102,241,0.1)]"
            : "bg-[#0f0f12] border-white/5 hover:border-white/15 hover:bg-white/[0.03]"
        }
        ${isClickable ? "cursor-pointer" : "cursor-default"}
      `}
    >
      <StatusDot status={task.status} />
      <div className="min-w-0 flex-1">
        <span
          className={`text-[11px] font-medium block truncate ${isCurrent ? "text-indigo-300" : "text-slate-300 group-hover/node:text-slate-200"}`}
        >
          {displayName}
        </span>
        <span className="text-[9px] font-mono text-slate-600 block truncate">
          {task.task_id}
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

function FlowArrow() {
  return (
    <div className="flex items-center justify-center w-8 shrink-0">
      <svg
        width="24"
        height="16"
        viewBox="0 0 24 16"
        className="text-slate-600"
      >
        <line
          x1="0"
          y1="8"
          x2="18"
          y2="8"
          stroke="currentColor"
          strokeWidth="1"
          strokeDasharray="3 2"
        />
        <polyline
          points="15,4 20,8 15,12"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        />
      </svg>
    </div>
  );
}

function BouncerNode({
  bouncer,
  onClick,
}: {
  bouncer: TopologyBouncer;
  onClick: () => void;
}) {
  const status = bouncer.status || "unknown";
  const cfg = getStatusStyle(status);

  return (
    <button
      type="button"
      onClick={onClick}
      className="group/node flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg border text-left transition-all duration-150 bg-teal-500/[0.04] border-teal-500/15 hover:border-teal-500/30 hover:bg-teal-500/[0.07] cursor-pointer"
    >
      <Radio className="w-3.5 h-3.5 text-teal-400/70 shrink-0" />
      <div className="min-w-0 flex-1">
        <span className="text-[11px] font-medium block truncate text-teal-200/80 group-hover/node:text-teal-200">
          {bouncer.display_name}
        </span>
        <span className="text-[9px] font-mono text-slate-600 block truncate">
          {bouncer.sensor_name}
        </span>
      </div>
      <span
        className={`inline-block w-2 h-2 rounded-full shrink-0 ${cfg.dot} ${cfg.glow}`}
        title={cfg.label}
      />
    </button>
  );
}

function SectionLabel({
  label,
  icon,
  accentColor,
}: {
  label: string;
  icon: React.ReactNode;
  accentColor: string;
}) {
  return (
    <div className="flex items-center gap-1.5 pt-1 pb-0.5 px-0.5">
      {icon}
      <span
        className={`text-[8px] font-mono uppercase tracking-[0.12em] ${accentColor}`}
      >
        {label}
      </span>
      <span className="flex-1 h-px bg-slate-700/30" />
    </div>
  );
}

function BouncerDagGroup({
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

function NeedsPrefDagGroup({
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

function groupBouncersByDag(
  bouncers: TopologyBouncer[],
): Record<string, TopologyBouncer[]> {
  const groups: Record<string, TopologyBouncer[]> = {};
  for (const s of bouncers) {
    for (const dagId of s.dag_ids) {
      if (!groups[dagId]) groups[dagId] = [];
      groups[dagId].push(s);
    }
  }
  return groups;
}

function groupByDag(tasks: TopologyTask[]): Record<string, TopologyTask[]> {
  const groups: Record<string, TopologyTask[]> = {};
  for (const t of tasks) {
    const key = t.dag_id || "unassigned";
    if (!groups[key]) groups[key] = [];
    groups[key].push(t);
  }
  return groups;
}

function groupByTaskGroup(
  tasks: TopologyTask[],
): { grouped: Record<string, TopologyTask[]>; hasGroups: boolean } {
  const groups: Record<string, TopologyTask[]> = {};
  let hasGroups = false;
  for (const t of tasks) {
    const key = t.task_group_id || "_ungrouped";
    if (t.task_group_id) hasGroups = true;
    if (!groups[key]) groups[key] = [];
    groups[key].push(t);
  }
  return { grouped: groups, hasGroups };
}

function statusSummary(tasks: TopologyTask[]) {
  const counts: Record<string, number> = {};
  for (const t of tasks) {
    const s = t.status || "unknown";
    counts[s] = (counts[s] || 0) + 1;
  }
  return counts;
}

function TaskGroupLabel({ groupId }: { groupId: string }) {
  return (
    <div className="flex items-center gap-1.5 pt-1.5 pb-0.5 px-0.5">
      <span className="w-3 h-px bg-slate-700/60" />
      <span className="text-[8px] font-mono uppercase tracking-[0.12em] text-slate-600 whitespace-nowrap">
        {groupId.replace(/_/g, " ")}
      </span>
      <span className="flex-1 h-px bg-slate-700/30" />
    </div>
  );
}

function DownstreamDagGroup({
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
