import { create } from "zustand";

export interface DataProductState {
  selectedProductId: string | null;
  searchQuery: string;
  filtersOpen: boolean;
  teamFilters: Set<string>;
  scheduleFilters: Set<string>;
  setSelectedProductId: (id: string | null) => void;
  setSearchQuery: (query: string) => void;
  setFiltersOpen: (open: boolean) => void;
  toggleFilter: (dimension: "team" | "schedule", value: string) => void;
  clearAllFilters: () => void;
}

const FILTER_KEYS = {
  team: "teamFilters",
  schedule: "scheduleFilters",
} as const;

export const useDataProductStore = create<DataProductState>((set) => ({
  selectedProductId: null,
  searchQuery: "",
  filtersOpen: false,
  teamFilters: new Set<string>(),
  scheduleFilters: new Set<string>(),
  setSelectedProductId: (id) => {
    set({ selectedProductId: id });
    window.location.hash = "data-products";
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
      scheduleFilters: new Set<string>(),
    }),
}));
