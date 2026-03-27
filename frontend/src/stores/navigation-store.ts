import { create } from "zustand";
import type { TabType } from "@/lib/constants";

const VALID_TABS: TabType[] = ["catalog", "matrix", "dags", "bouncers", "ai", "admin"];

export function getTabFromHash(): TabType {
  const hash = window.location.hash.slice(1); // remove #
  return VALID_TABS.includes(hash as TabType) ? (hash as TabType) : "catalog";
}

interface NavigationState {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
}

export const useNavigationStore = create<NavigationState>((set) => ({
  activeTab: getTabFromHash(),
  setActiveTab: (tab) => {
    set({ activeTab: tab });
    window.location.hash = tab;
  },
}));
