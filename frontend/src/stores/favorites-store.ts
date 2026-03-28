import { create } from "zustand";

const STORAGE_KEY = "etlnexus:favorites";

function loadFavorites(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveFavorites(ids: string[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // localStorage unavailable
  }
}

interface FavoritesState {
  favoriteIds: string[];
  toggleFavorite: (id: string) => void;
  isFavorite: (id: string) => boolean;
}

export const useFavoritesStore = create<FavoritesState>((set, get) => ({
  favoriteIds: loadFavorites(),
  toggleFavorite: (id) => {
    const current = get().favoriteIds;
    const next = current.includes(id)
      ? current.filter((fid) => fid !== id)
      : [...current, id];
    saveFavorites(next);
    set({ favoriteIds: next });
  },
  isFavorite: (id) => get().favoriteIds.includes(id),
}));
