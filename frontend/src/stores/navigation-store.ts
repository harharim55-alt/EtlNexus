import { create } from "zustand";
import type { TabType } from "@/lib/constants";

const VALID_TABS: TabType[] = ["data-products", "tables", "ai"];
const DEFAULT_TAB: TabType = "data-products";

export interface ParsedHash {
  tab: TabType;
}

/** Parse hash like #tables */
export function parseHash(): ParsedHash {
  const raw = window.location.hash.slice(1); // remove #
  const segments = raw.split("/").filter(Boolean);
  const tab = VALID_TABS.includes(segments[0] as TabType)
    ? (segments[0] as TabType)
    : DEFAULT_TAB;
  return { tab };
}

/** Build a hash string from a tab */
export function buildHash(tab: TabType): string {
  return tab;
}

export interface Breadcrumb {
  tab: TabType;
  label: string;
}

interface NavigationState {
  activeTab: TabType;
  breadcrumbs: Breadcrumb[];
  setActiveTab: (tab: TabType) => void;
  pushBreadcrumb: (crumb: Breadcrumb) => void;
  popBreadcrumb: () => void;
  clearBreadcrumbs: () => void;
}

export const useNavigationStore = create<NavigationState>((set, get) => ({
  activeTab: parseHash().tab,
  breadcrumbs: [],
  setActiveTab: (tab) => {
    set({ activeTab: tab, breadcrumbs: [] });
    window.location.hash = tab;
  },
  pushBreadcrumb: (crumb) => {
    set((state) => ({ breadcrumbs: [...state.breadcrumbs, crumb] }));
  },
  popBreadcrumb: () => {
    const { breadcrumbs } = get();
    if (breadcrumbs.length === 0) return;
    const remaining = breadcrumbs.slice(0, -1);
    const target = remaining[remaining.length - 1];
    set({ breadcrumbs: remaining });
    if (target) {
      set({ activeTab: target.tab });
      window.location.hash = target.tab;
    }
  },
  clearBreadcrumbs: () => {
    set({ breadcrumbs: [] });
  },
}));
