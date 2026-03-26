import { create } from "zustand";

export interface RunSelectorState {
  /** null = "Latest" (current/live data) */
  selectedDagRunId: string | null;
  /** The DAG this run belongs to */
  selectedRunDagId: string | null;
  /** Run start_date ISO string for display */
  selectedRunDate: string | null;
  /** Run status for display */
  selectedRunStatus: string | null;

  selectRun: (
    dagRunId: string,
    dagId: string,
    date: string | null,
    status: string,
  ) => void;
  /** Go back to "Latest" (live data) */
  clearRun: () => void;
}

export const useRunSelectorStore = create<RunSelectorState>((set) => ({
  selectedDagRunId: null,
  selectedRunDagId: null,
  selectedRunDate: null,
  selectedRunStatus: null,

  selectRun: (dagRunId, dagId, date, status) =>
    set({
      selectedDagRunId: dagRunId,
      selectedRunDagId: dagId,
      selectedRunDate: date,
      selectedRunStatus: status,
    }),

  clearRun: () =>
    set({
      selectedDagRunId: null,
      selectedRunDagId: null,
      selectedRunDate: null,
      selectedRunStatus: null,
    }),
}));

/**
 * Returns { dag_run_id } when a run is selected, undefined for "Latest".
 * Use this in hooks that need to conditionally pass run context.
 */
export function useRunParams(): { dag_run_id: string } | undefined {
  const dagRunId = useRunSelectorStore((s) => s.selectedDagRunId);
  return dagRunId ? { dag_run_id: dagRunId } : undefined;
}
