import { Radio } from "lucide-react";
import { getStatusStyle } from "@/lib/status-config";
import type { TopologyTask, TopologyBouncer } from "@/types/topology";

export function StatusDot({ status }: { status: string }) {
  const cfg = getStatusStyle(status);
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full shrink-0 ${cfg.dot} ${cfg.glow}`}
      title={cfg.label}
    />
  );
}

export function TaskNode({
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

export function FlowArrow() {
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

export function BouncerNode({
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

export function SectionLabel({
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

export function TaskGroupLabel({ groupId }: { groupId: string }) {
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
