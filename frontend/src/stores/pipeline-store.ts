import { create } from "zustand";

interface PipelineState {
  selectedPipelineId: string | null;
  selectedDagId: string | null;
  searchQuery: string;
  setSelectedPipelineId: (id: string | null) => void;
  setSelectedDagId: (dagId: string | null) => void;
  setSearchQuery: (query: string) => void;
}

export const usePipelineStore = create<PipelineState>((set) => ({
  selectedPipelineId: null,
  selectedDagId: null,
  searchQuery: "",
  setSelectedPipelineId: (id) => set({ selectedPipelineId: id, selectedDagId: null }),
  setSelectedDagId: (dagId) => set({ selectedDagId: dagId }),
  setSearchQuery: (query) => set({ searchQuery: query }),
}));
