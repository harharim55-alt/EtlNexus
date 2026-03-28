import { create } from "zustand";
import { useRunSelectorStore } from "./run-selector-store";
import { buildHash } from "./navigation-store";

export interface PipelineState {
  selectedPipelineId: string | null;
  selectedDagId: string | null;
  searchQuery: string;
  filtersOpen: boolean;
  teamFilters: Set<string>;
  dagFilters: Set<string>;
  statusFilters: Set<string>;
  setSelectedPipelineId: (id: string | null) => void;
  setSelectedDagId: (dagId: string | null) => void;
  setSearchQuery: (query: string) => void;
  setFiltersOpen: (open: boolean) => void;
  toggleFilter: (dimension: "team" | "dag" | "status", value: string) => void;
  clearAllFilters: () => void;
}

const FILTER_KEYS = {
  team: "teamFilters",
  dag: "dagFilters",
  status: "statusFilters",
} as const;

// NOTE: This store writes to window.location.hash when the selected pipeline
// changes, as part of a bidirectional sync pattern with App.tsx (which listens
// for "hashchange" to propagate URL changes back into stores). This keeps the
// URL in sync for bookmarking and browser back/forward navigation.
export const usePipelineStore = create<PipelineState>((set) => ({
  selectedPipelineId: null,
  selectedDagId: null,
  searchQuery: "",
  filtersOpen: false,
  teamFilters: new Set<string>(),
  dagFilters: new Set<string>(),
  statusFilters: new Set<string>(),
  setSelectedPipelineId: (id) => {
    useRunSelectorStore.getState().clearRun();
    set({ selectedPipelineId: id, selectedDagId: null });
    window.location.hash = buildHash("catalog", id);
  },
  setSelectedDagId: (dagId) => set({ selectedDagId: dagId }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setFiltersOpen: (open) => set({ filtersOpen: open }),
  toggleFilter: (dimension, value) =>
    set((state) => {
      const key = FILTER_KEYS[dimension];
      const current = new Set(state[key]);
      if (current.has(value)) {
        current.delete(value);
      } else {
        current.add(value);
      }
      return { [key]: current };
    }),
  clearAllFilters: () =>
    set({
      teamFilters: new Set<string>(),
      dagFilters: new Set<string>(),
      statusFilters: new Set<string>(),
    }),
}));
