import { create } from "zustand";

export type Theme = "dark" | "light";

const STORAGE_KEY = "etlnexus:theme";

/**
 * Resolve the startup theme.
 *
 * Reads only our own persisted choice from localStorage; the OS/browser
 * `prefers-color-scheme` is intentionally NOT consulted, so a given mode
 * renders identically on every machine. Falls back to a fixed "dark" default.
 */
function getInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
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
  toggleTheme: () => void;
}

// Apply initial theme immediately (matches the pre-paint script in index.html).
applyTheme(getInitialTheme());

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: getInitialTheme(),
  setTheme: (theme) => {
    applyTheme(theme);
    set({ theme });
  },
  toggleTheme: () => {
    const next: Theme = get().theme === "dark" ? "light" : "dark";
    applyTheme(next);
    set({ theme: next });
  },
}));
