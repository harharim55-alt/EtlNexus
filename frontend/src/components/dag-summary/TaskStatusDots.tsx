import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { DagTaskSummary } from "@/types/dag-summary";

function dotColor(status: string): string {
  switch (status) {
    case "success":
      return "bg-emerald-500";
    case "failed":
      return "bg-rose-500";
    case "upstream_failed":
      return "bg-orange-500";
    case "running":
      return "bg-amber-500";
    case "queued":
      return "bg-sky-500";
    default:
      return "bg-slate-600";
  }
}

interface TaskStatusDotsProps {
  tasks: DagTaskSummary[];
}

export function TaskStatusDots({ tasks }: TaskStatusDotsProps) {
  if (tasks.length === 0) return null;

  return (
    <div className="flex items-center gap-[5px] flex-wrap">
      {tasks.map((task) => (
        <Tooltip key={task.task_id}>
          <TooltipTrigger
            className={`w-[7px] h-[7px] rounded-full ${dotColor(task.status)} transition-transform hover:scale-150 cursor-default`}
          />
          <TooltipContent
            side="top"
            className="bg-[#18181b] border border-white/10 text-white text-[10px] font-mono px-2 py-1"
          >
            <span className="text-slate-400">{task.task_id}</span>
            {task.pipeline_name && (
              <span className="text-indigo-400 ml-1.5">
                {task.pipeline_name}
              </span>
            )}
            <span
              className={`ml-1.5 ${
                task.status === "success"
                  ? "text-emerald-400"
                  : task.status === "failed"
                    ? "text-rose-400"
                    : task.status === "upstream_failed"
                      ? "text-orange-400"
                      : task.status === "running"
                        ? "text-amber-400"
                        : task.status === "queued"
                          ? "text-sky-400"
                          : "text-slate-500"
              }`}
            >
              {task.status}
            </span>
          </TooltipContent>
        </Tooltip>
      ))}
    </div>
  );
}
