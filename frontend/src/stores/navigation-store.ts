import { create } from "zustand";
import type { TabType } from "@/lib/constants";

const VALID_TABS: TabType[] = ["catalog", "data-products", "matrix", "dags", "bouncers", "ai", "admin"];

export interface ParsedHash {
  tab: TabType;
  pipelineId?: string;
  dagRunId?: string;
}

/** Parse hash like #catalog/{pipelineId}/run/{dagRunId} */
export function parseHash(): ParsedHash {
  const raw = window.location.hash.slice(1); // remove #
  const segments = raw.split("/").filter(Boolean);
  const tab = VALID_TABS.includes(segments[0] as TabType)
    ? (segments[0] as TabType)
    : "catalog";

  const result: ParsedHash = { tab };

  if (tab === "catalog" && segments.length >= 2) {
    result.pipelineId = segments[1];
    if (segments[2] === "run" && segments[3]) {
      result.dagRunId = segments[3];
    }
  }

  return result;
}

/** Build a hash string from parts */
export function buildHash(
  tab: TabType,
  pipelineId?: string | null,
  dagRunId?: string | null,
): string {
  if (tab === "catalog" && pipelineId) {
    if (dagRunId) return `catalog/${pipelineId}/run/${dagRunId}`;
    return `catalog/${pipelineId}`;
  }
  return tab;
}

export interface Breadcrumb {
  tab: TabType;
  label: string;
  pipelineId?: string;
}

interface NavigationState {
  activeTab: TabType;
  breadcrumbs: Breadcrumb[];
  setActiveTab: (tab: TabType) => void;
  pushBreadcrumb: (crumb: Breadcrumb) => void;
  popBreadcrumb: () => void;
  clearBreadcrumbs: () => void;
}

// NOTE: This store intentionally writes to window.location.hash as part of a
// bidirectional sync pattern. App.tsx listens for "hashchange" events and
// propagates the parsed hash back into the relevant stores, enabling browser
// back/forward navigation. Stores are the "source of truth" for programmatic
// navigation; the URL hash is kept in sync as a side effect.
export const useNavigationStore = create<NavigationState>((set, get) => ({
  activeTab: parseHash().tab,
  breadcrumbs: [],
  setActiveTab: (tab) => {
    set({ activeTab: tab, breadcrumbs: [] });
    // Sync hash so the URL reflects the active tab (bidirectional sync with App.tsx)
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
      window.location.hash = target.pipelineId
        ? buildHash(target.tab, target.pipelineId)
        : target.tab;
    }
  },
  clearBreadcrumbs: () => {
    set({ breadcrumbs: [] });
  },
}));
