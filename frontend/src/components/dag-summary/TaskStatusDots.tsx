import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getStatusStyle } from "@/lib/status-config";
import { stripDummy } from "@/lib/format";
import type { DagTaskSummary } from "@/types/dag-summary";

interface TaskStatusDotsProps {
  tasks: DagTaskSummary[];
}

export function TaskStatusDots({ tasks }: TaskStatusDotsProps) {
  if (tasks.length === 0) return null;

  return (
    <div className="flex items-center gap-[5px] flex-wrap">
      {tasks.map((task) => {
        const cfg = getStatusStyle(task.status);
        return (
          <Tooltip key={task.task_id}>
            <TooltipTrigger
              className={`w-[7px] h-[7px] rounded-full ${cfg.dot} transition-transform hover:scale-150 cursor-default`}
            />
            <TooltipContent
              side="top"
              className="bg-card border border-border-prominent text-foreground text-[10px] font-mono px-2 py-1"
            >
              <span className="text-text-secondary">{task.task_id}</span>
              {task.pipeline_name && (
                <span className="text-indigo-400 ml-1.5">
                  {stripDummy(task.pipeline_name)}
                </span>
              )}
              <span className={`ml-1.5 ${cfg.text}`}>
                {task.status}
              </span>
            </TooltipContent>
          </Tooltip>
        );
      })}
    </div>
  );
}
