import { create } from "zustand";

interface BouncerState {
  selectedBouncers: string[];
  teamFilter: string | undefined;
  topologyMode: "union" | "intersection";
  searchQuery: string;
  toggleBouncer: (bouncerName: string) => void;
  clearBouncers: () => void;
  setTeamFilter: (team: string | undefined) => void;
  setTopologyMode: (mode: "union" | "intersection") => void;
  setSearchQuery: (query: string) => void;
}

export const useBouncerStore = create<BouncerState>((set) => ({
  selectedBouncers: [],
  teamFilter: undefined,
  topologyMode: "union",
  searchQuery: "",
  toggleBouncer: (bouncerName) =>
    set((state) => ({
      selectedBouncers: state.selectedBouncers.includes(bouncerName)
        ? state.selectedBouncers.filter((s) => s !== bouncerName)
        : [...state.selectedBouncers, bouncerName],
    })),
  clearBouncers: () => set({ selectedBouncers: [] }),
  setTeamFilter: (team) => set({ teamFilter: team }),
  setTopologyMode: (mode) => set({ topologyMode: mode }),
  setSearchQuery: (query) => set({ searchQuery: query }),
}));
