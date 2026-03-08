import { create } from "zustand";
import type { TabType } from "@/lib/constants";

interface NavigationState {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
}

export const useNavigationStore = create<NavigationState>((set) => ({
  activeTab: "catalog",
  setActiveTab: (tab) => set({ activeTab: tab }),
}));
