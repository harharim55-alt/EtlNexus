import { create } from "zustand";
import { useRunSelectorStore } from "./run-selector-store";
import { buildHash } from "./navigation-store";

export interface DataProductState {
  selectedProductId: string | null;
  searchQuery: string;
  filtersOpen: boolean;
  teamFilters: Set<string>;
  networkFilters: Set<string>;
  tagFilters: Set<string>;
  setSelectedProductId: (id: string | null) => void;
  setSearchQuery: (query: string) => void;
  setFiltersOpen: (open: boolean) => void;
  toggleFilter: (dimension: "team" | "network" | "tag", value: string) => void;
  clearAllFilters: () => void;
}

const FILTER_KEYS = {
  team: "teamFilters",
  network: "networkFilters",
  tag: "tagFilters",
} as const;

export const useDataProductStore = create<DataProductState>((set) => ({
  selectedProductId: null,
  searchQuery: "",
  filtersOpen: false,
  teamFilters: new Set<string>(),
  networkFilters: new Set<string>(),
  tagFilters: new Set<string>(),
  setSelectedProductId: (id) => {
    useRunSelectorStore.getState().clearRun();
    set({ selectedProductId: id });
    window.location.hash = buildHash("data-products", id);
  },
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
      networkFilters: new Set<string>(),
      tagFilters: new Set<string>(),
    }),
}));
