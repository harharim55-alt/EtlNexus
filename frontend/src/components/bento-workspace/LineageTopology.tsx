import { useEffect, useState } from "react";
import { Layers, Lock, Network, Sparkles } from "lucide-react";
import { useLineage } from "@/hooks/use-lineage";
import { useTopology } from "@/hooks/use-topology";
import { usePipelineStore } from "@/stores/pipeline-store";
import { Skeleton } from "@/components/ui/skeleton";
import type { TopologyTask } from "@/types/topology";

interface LineageTopologyProps {
  pipelineId: string;
}

const STATUS_CONFIG: Record<
  string,
  { dot: string; glow: string; label: string }
> = {
  success: {
    dot: "bg-emerald-400",
    glow: "shadow-[0_0_8px_rgba(52,211,153,0.7)]",
    label: "Success",
  },
  failed: {
    dot: "bg-rose-400",
    glow: "shadow-[0_0_8px_rgba(251,113,133,0.7)]",
    label: "Failed",
  },
  running: {
    dot: "bg-amber-400 animate-pulse",
    glow: "shadow-[0_0_8px_rgba(251,191,36,0.7)]",
    label: "Running",
  },
  unknown: {
    dot: "bg-slate-500",
    glow: "",
    label: "Unknown",
  },
};

function StatusDot({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.unknown;
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
  const displayName = task.pipeline_name ?? task.task_id.replace(/_/g, " ");
  const isClickable = !isCurrent && !!task.pipeline_id;
  const cfg = STATUS_CONFIG[task.status] ?? STATUS_CONFIG.unknown;

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
        className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
          task.status === "success"
            ? "text-emerald-400/70 bg-emerald-500/5"
            : task.status === "failed"
              ? "text-rose-400/70 bg-rose-500/5"
              : task.status === "running"
                ? "text-amber-400/70 bg-amber-500/5"
                : "text-slate-500 bg-white/[0.02]"
        }`}
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

function UpstreamGroup({
  label,
  icon,
  tasks,
  onTaskClick,
  accentColor,
}: {
  label: string;
  icon: React.ReactNode;
  tasks: TopologyTask[];
  onTaskClick: (id: string) => void;
  accentColor: string;
}) {
  if (tasks.length === 0) return null;
  return (
    <div>
      <div className={`flex items-center gap-1.5 mb-1.5`}>
        {icon}
        <span
          className={`text-[9px] font-mono uppercase tracking-[0.15em] ${accentColor}`}
        >
          {label}
        </span>
      </div>
      <div className="flex flex-col gap-1.5">
        {tasks.map((t) => (
          <TaskNode
            key={t.task_id}
            task={t}
            onClick={() => t.pipeline_id && onTaskClick(t.pipeline_id)}
          />
        ))}
      </div>
    </div>
  );
}

export function LineageTopology({ pipelineId }: LineageTopologyProps) {
  const [selectedDagId, setSelectedDagId] = useState<string | null>(null);
  useEffect(() => setSelectedDagId(null), [pipelineId]);
  const { data: topology, isLoading: topoLoading } = useTopology(pipelineId, selectedDagId);
  const { data: lineage, isLoading: lineageLoading } = useLineage(pipelineId);
  const setSelectedPipelineId = usePipelineStore(
    (s) => s.setSelectedPipelineId,
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
    (topology.upstream_needs.length > 0 ||
      topology.upstream_prefers.length > 0 ||
      topology.downstream.length > 0);

  const currentTask: TopologyTask = {
    task_id: topology?.pipeline_task_id ?? "",
    pipeline_name: null,
    pipeline_id: pipelineId,
    status: topology?.pipeline_status ?? "unknown",
    dag_id: topology?.dag_ids?.[0] ?? "",
  };

  const hasUpstream =
    (topology?.upstream_needs.length ?? 0) > 0 ||
    (topology?.upstream_prefers.length ?? 0) > 0;

  return (
    <div className="col-span-12 lg:col-span-8 bg-[#18181b] border border-white/5 rounded-2xl p-6 relative overflow-hidden group">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

      <div className="flex items-center justify-between mb-5">
        <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
          <Network className="w-3.5 h-3.5" /> Pipeline Topology
        </h3>
        {topology?.dag_ids && topology.dag_ids.length > 0 && (
          <div className="flex items-center gap-1.5">
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
          </div>
        )}
      </div>

      {hasTopology ? (
        <div className="flex items-start justify-center gap-0">
          {/* Upstream column — split into needs & prefers */}
          {hasUpstream && (
            <>
              <div className="flex-1 min-w-0 max-w-[240px] space-y-3">
                <UpstreamGroup
                  label="Needs"
                  icon={<Lock className="w-3 h-3 text-orange-400/70" />}
                  tasks={topology!.upstream_needs}
                  onTaskClick={setSelectedPipelineId}
                  accentColor="text-orange-400/70"
                />
                <UpstreamGroup
                  label="Prefers"
                  icon={<Sparkles className="w-3 h-3 text-sky-400/70" />}
                  tasks={topology!.upstream_prefers}
                  onTaskClick={setSelectedPipelineId}
                  accentColor="text-sky-400/70"
                />
              </div>
              <div className="flex items-center self-center pt-3">
                <FlowArrow />
              </div>
            </>
          )}

          {/* Current pipeline (center) */}
          <div className="flex-1 min-w-0 max-w-[240px] self-center">
            <span className="text-[9px] font-mono uppercase tracking-[0.15em] text-slate-600 mb-2 block text-center">
              Current
            </span>
            <TaskNode task={currentTask} isCurrent />
          </div>

          {/* Downstream column */}
          {topology!.downstream.length > 0 && (
            <>
              <div className="flex items-center self-center pt-3">
                <FlowArrow />
              </div>
              <div className="flex-1 min-w-0 max-w-[240px] self-center">
                <span className="text-[9px] font-mono uppercase tracking-[0.15em] text-slate-600 mb-2 block text-center">
                  Downstream
                </span>
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
              </div>
            </>
          )}
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
    </div>
  );
}
