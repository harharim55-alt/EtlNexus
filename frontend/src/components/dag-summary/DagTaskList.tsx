import { STATUS_SEVERITY_ORDER } from "@/lib/status-config";
import { TaskStatusDots } from "./TaskStatusDots";
import type { DagTaskSummary } from "@/types/dag-summary";

/* ── Props ────────────────────────────────────────────────────────── */

interface DagTaskListProps {
  tasks: DagTaskSummary[];
}

/* ── Component ─────────────────────────────────────────────────────── */

export function DagTaskList({ tasks }: DagTaskListProps) {
  const sortedTasks = [...tasks].sort((a, b) => {
    const ai = STATUS_SEVERITY_ORDER.indexOf(a.status);
    const bi = STATUS_SEVERITY_ORDER.indexOf(b.status);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  return (
    <div className="pt-2 border-t border-white/5">
      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-[9px] font-mono uppercase tracking-widest text-slate-600">
          Tasks
        </span>
      </div>
      <TaskStatusDots tasks={sortedTasks} />
    </div>
  );
}
