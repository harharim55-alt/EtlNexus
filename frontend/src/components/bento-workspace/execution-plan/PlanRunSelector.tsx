import { useState, useRef, useEffect } from "react";
import { ChevronDown, Loader2 } from "lucide-react";
import { useExecutionPlanRuns } from "@/hooks/use-execution-plan";
import { formatDateFull } from "@/lib/format";

export function RunPicker({
  pipelineId,
  currentRunId,
  onSelect,
}: {
  pipelineId: string;
  currentRunId: string;
  onSelect: (dagRunId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useExecutionPlanRuns(pipelineId);

  const allRuns = data?.pages.flatMap((p) => p.items) ?? [];
  const total = data?.pages[0]?.total ?? 0;

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  // Infinite scroll: load more when scrolled near bottom
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !open) return;
    function onScroll() {
      if (!el || !hasNextPage || isFetchingNextPage) return;
      if (el.scrollTop + el.clientHeight >= el.scrollHeight - 40) {
        fetchNextPage();
      }
    }
    el.addEventListener("scroll", onScroll);
    return () => el.removeEventListener("scroll", onScroll);
  }, [open, hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (total <= 1) return null;

  const current = allRuns.find((r) => r.dag_run_id === currentRunId);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer inline-flex items-center gap-1 text-indigo-300 bg-indigo-500/15 border-indigo-500/30"
      >
        {current ? formatDateFull(current.start_date) : "Latest"}
        <ChevronDown className={`w-2.5 h-2.5 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="absolute top-full right-0 mt-1 z-50 bg-card border border-border-prominent rounded-xl shadow-xl overflow-hidden min-w-[220px]">
          <div
            ref={scrollRef}
            className="max-h-[280px] overflow-y-auto custom-scrollbar"
          >
            {allRuns.map((run) => (
              <button
                key={run.dag_run_id}
                type="button"
                onClick={() => { onSelect(run.dag_run_id); setOpen(false); }}
                className={`w-full text-left px-3 py-2 text-[11px] font-mono transition-colors cursor-pointer flex items-center justify-between gap-3 ${
                  run.dag_run_id === currentRunId
                    ? "bg-indigo-500/10 text-indigo-300"
                    : "text-text-secondary hover:bg-hover-bg hover:text-text-primary"
                }`}
              >
                <span>{formatDateFull(run.start_date)}</span>
                <span className="text-[9px] text-text-faint">{run.dag_id}</span>
              </button>
            ))}
            {isFetchingNextPage && (
              <div className="flex justify-center py-2">
                <Loader2 className="w-3.5 h-3.5 text-text-faint animate-spin" />
              </div>
            )}
          </div>
          {total > 0 && (
            <div className="px-3 py-1.5 border-t border-border text-[9px] font-mono text-text-faint text-center">
              {allRuns.length} of {total} runs
            </div>
          )}
        </div>
      )}
    </div>
  );
}
