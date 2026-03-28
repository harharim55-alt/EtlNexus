import { create } from "zustand";

interface ComparisonState {
  pipelineA: string | null;
  pipelineB: string | null;
  setPipelineA: (id: string | null) => void;
  setPipelineB: (id: string | null) => void;
  isComparing: boolean;
  startComparison: (idA: string, idB: string) => void;
  clearComparison: () => void;
}

export const useComparisonStore = create<ComparisonState>((set) => ({
  pipelineA: null,
  pipelineB: null,
  isComparing: false,
  setPipelineA: (id) =>
    set((state) => {
      const hasB = state.pipelineB != null;
      return { pipelineA: id, isComparing: id != null && hasB };
    }),
  setPipelineB: (id) =>
    set((state) => {
      const hasA = state.pipelineA != null;
      return { pipelineB: id, isComparing: hasA && id != null };
    }),
  startComparison: (idA, idB) =>
    set({ pipelineA: idA, pipelineB: idB, isComparing: true }),
  clearComparison: () =>
    set({ pipelineA: null, pipelineB: null, isComparing: false }),
}));
