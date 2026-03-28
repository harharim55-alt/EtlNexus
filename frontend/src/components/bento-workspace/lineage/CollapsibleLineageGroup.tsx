import { useState, useRef, useEffect, useCallback } from "react";
import { ChevronRight } from "lucide-react";
import { getStatusStyle } from "@/lib/status-config";
import type { TopologyTask } from "@/types/topology";
import { TaskNode, TaskGroupLabel } from "./LineageNodes";
import { groupByTaskGroup, statusSummary } from "./lineage-utils";

/* ── Props ────────────────────────────────────────────────────────── */

interface CollapsibleLineageGroupProps {
  dagId: string;
  tasks: TopologyTask[];
  onTaskClick: (pipelineId: string) => void;
  defaultOpen: boolean;
  /** Optional border color class for the group container */
  borderColor?: string;
  /** Optional background class for the group container */
  bgColor?: string;
  /** Optional chevron icon color */
  chevronColor?: string;
  /** Whether to show status summary pills in the header */
  showStatusSummary?: boolean;
  /** Pre-label content (e.g. section labels for needs/prefers) */
  children?: React.ReactNode;
}

/* ── Component ─────────────────────────────────────────────────────── */

export function CollapsibleLineageGroup({
  dagId,
  tasks,
  onTaskClick,
  defaultOpen,
  borderColor = "border-border",
  bgColor = "bg-hover-bg",
  chevronColor = "text-text-muted",
  showStatusSummary = true,
  children,
}: CollapsibleLineageGroupProps) {
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

  const summary = showStatusSummary ? statusSummary(tasks) : {};
  const hasFailure = (summary.failed ?? 0) > 0;

  return (
    <div className={`rounded-lg border ${borderColor} ${bgColor} overflow-hidden`}>
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="flex items-center gap-2 w-full px-2.5 py-2 text-left hover:bg-hover-bg transition-colors cursor-pointer"
      >
        <ChevronRight
          className={`w-3 h-3 ${chevronColor} shrink-0 transition-transform duration-200 ${isOpen ? "rotate-90" : ""}`}
        />
        <span className="text-[10px] font-mono text-text-secondary truncate flex-1">
          {dagId.replace(/_/g, " ")}
        </span>

        {showStatusSummary && (
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
        )}

        <span
          className={`text-[9px] font-mono tabular-nums shrink-0 ${hasFailure ? "text-rose-400/60" : "text-text-faint"}`}
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
          {children}
          {!children && (
            <TaskList tasks={tasks} onTaskClick={onTaskClick} />
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Shared task list with task-group support ─────────────────────── */

export function TaskList({
  tasks,
  onTaskClick,
}: {
  tasks: TopologyTask[];
  onTaskClick: (pipelineId: string) => void;
}) {
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
  return (
    <>
      {Object.entries(grouped).map(([gId, gTasks]) => (
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
      ))}
    </>
  );
}
