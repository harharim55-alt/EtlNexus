import { create } from "zustand";

export type Theme = "dark" | "light" | "pink";

const STORAGE_KEY = "etlnexus:theme";

function getInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "pink" || stored === "dark") return stored;
  } catch {
    // localStorage unavailable
  }
  return "dark";
}

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // localStorage unavailable
  }
}

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  cycleTheme: () => void;
}

// Apply initial theme immediately
applyTheme(getInitialTheme());

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: getInitialTheme(),
  setTheme: (theme) => {
    applyTheme(theme);
    set({ theme });
  },
  cycleTheme: () => {
    const order: Theme[] = ["dark", "light", "pink"];
    const current = get().theme;
    const next = order[(order.indexOf(current) + 1) % order.length];
    applyTheme(next);
    set({ theme: next });
  },
}));
