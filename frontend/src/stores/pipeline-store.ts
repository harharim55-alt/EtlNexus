import { create } from "zustand";

interface PipelineState {
  selectedPipelineId: string | null;
  searchQuery: string;
  setSelectedPipelineId: (id: string | null) => void;
  setSearchQuery: (query: string) => void;
}

export const usePipelineStore = create<PipelineState>((set) => ({
  selectedPipelineId: null,
  searchQuery: "",
  setSelectedPipelineId: (id) => set({ selectedPipelineId: id }),
  setSearchQuery: (query) => set({ searchQuery: query }),
}));
