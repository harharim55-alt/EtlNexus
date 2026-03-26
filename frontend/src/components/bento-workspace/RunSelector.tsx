import { useState, useRef, useEffect } from "react";
import { ChevronDown, Loader2, Radio, Clock } from "lucide-react";
import { useRuns } from "@/hooks/use-runs";
import { useRunSelectorStore } from "@/stores/run-selector-store";
import { formatDateFull, formatDuration } from "@/lib/format";
import { getStatusStyle } from "@/lib/status-config";

interface RunSelectorProps {
  pipelineId: string;
}

export function RunSelector({ pipelineId }: RunSelectorProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const selectedDagRunId = useRunSelectorStore((s) => s.selectedDagRunId);
  const selectedRunDate = useRunSelectorStore((s) => s.selectedRunDate);
  const selectedRunStatus = useRunSelectorStore((s) => s.selectedRunStatus);
  const selectRun = useRunSelectorStore((s) => s.selectRun);
  const clearRun = useRunSelectorStore((s) => s.clearRun);

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useRuns(pipelineId);

  const allRuns = data?.pages.flatMap((p) => p.items) ?? [];
  const total = data?.pages[0]?.total ?? 0;

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  // Infinite scroll
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

  const isLatest = selectedDagRunId === null;
  const statusCfg = selectedRunStatus
    ? getStatusStyle(selectedRunStatus)
    : null;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`text-[11px] font-mono px-3 py-1.5 rounded-lg border transition-all cursor-pointer inline-flex items-center gap-2 ${
          isLatest
            ? "text-emerald-300 bg-emerald-500/10 border-emerald-500/20 hover:bg-emerald-500/15"
            : "text-indigo-300 bg-indigo-500/10 border-indigo-500/20 hover:bg-indigo-500/15"
        }`}
      >
        {isLatest ? (
          <>
            <Radio className="w-3 h-3 animate-pulse" />
            <span>Latest</span>
          </>
        ) : (
          <>
            <Clock className="w-3 h-3" />
            <span>{formatDateFull(selectedRunDate)}</span>
            {statusCfg && (
              <span
                className={`w-1.5 h-1.5 rounded-full ${statusCfg.dot.replace(" animate-pulse", "")}`}
              />
            )}
          </>
        )}
        <ChevronDown
          className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute top-full right-0 mt-1 z-50 bg-[#18181b] border border-white/10 rounded-xl shadow-2xl shadow-black/60 overflow-hidden min-w-[280px]">
          {/* "Latest (live)" option */}
          <button
            type="button"
            onClick={() => {
              clearRun();
              setOpen(false);
            }}
            className={`w-full text-left px-4 py-2.5 text-[11px] font-mono transition-colors cursor-pointer flex items-center gap-3 border-b border-white/5 ${
              isLatest
                ? "bg-emerald-500/10 text-emerald-300"
                : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
            }`}
          >
            <Radio
              className={`w-3 h-3 ${isLatest ? "text-emerald-400 animate-pulse" : "text-slate-600"}`}
            />
            <span className="flex-1">Latest (live)</span>
            {isLatest && (
              <span className="text-[9px] uppercase tracking-wider text-emerald-500">
                Active
              </span>
            )}
          </button>

          {/* Run list */}
          <div
            ref={scrollRef}
            className="max-h-[320px] overflow-y-auto custom-scrollbar"
          >
            {allRuns.map((run) => {
              const cfg = getStatusStyle(run.status);
              const isSelected = run.dag_run_id === selectedDagRunId;
              return (
                <button
                  key={run.dag_run_id}
                  type="button"
                  onClick={() => {
                    selectRun(
                      run.dag_run_id,
                      run.dag_id,
                      run.start_date,
                      run.status,
                    );
                    setOpen(false);
                  }}
                  className={`w-full text-left px-4 py-2 text-[11px] font-mono transition-colors cursor-pointer flex items-center gap-3 ${
                    isSelected
                      ? "bg-indigo-500/10 text-indigo-300"
                      : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${cfg.dot.replace(" animate-pulse", "")}`}
                  />
                  <span className="flex-1 min-w-0 truncate">
                    {formatDateFull(run.start_date)}
                  </span>
                  {run.duration_seconds != null && (
                    <span className="text-[10px] text-slate-600 shrink-0">
                      {formatDuration(run.duration_seconds)}
                    </span>
                  )}
                </button>
              );
            })}
            {isFetchingNextPage && (
              <div className="flex justify-center py-2">
                <Loader2 className="w-3.5 h-3.5 text-slate-600 animate-spin" />
              </div>
            )}
          </div>

          {/* Footer */}
          {total > 0 && (
            <div className="px-3 py-1.5 border-t border-white/5 text-[9px] font-mono text-slate-600 text-center">
              {allRuns.length} of {total} runs
            </div>
          )}
        </div>
      )}
    </div>
  );
}
