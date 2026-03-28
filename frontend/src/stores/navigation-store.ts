import { create } from "zustand";
import type { TabType } from "@/lib/constants";

const VALID_TABS: TabType[] = ["catalog", "matrix", "dags", "bouncers", "ai", "admin"];

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

/** @deprecated Use parseHash() for full context */
export function getTabFromHash(): TabType {
  return parseHash().tab;
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

export const useNavigationStore = create<NavigationState>((set, get) => ({
  activeTab: parseHash().tab,
  breadcrumbs: [],
  setActiveTab: (tab) => {
    set({ activeTab: tab, breadcrumbs: [] });
    // When switching tabs, don't carry pipeline context to non-catalog tabs
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
