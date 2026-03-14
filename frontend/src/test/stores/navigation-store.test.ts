import { describe, it, expect, beforeEach } from "vitest";
import { useNavigationStore } from "@/stores/navigation-store";
import type { TabType } from "@/lib/constants";

beforeEach(() => {
  useNavigationStore.setState({ activeTab: "catalog" });
});

describe("useNavigationStore — initial state", () => {
  it("defaults to 'catalog' tab", () => {
    expect(useNavigationStore.getState().activeTab).toBe("catalog");
  });
});

describe("useNavigationStore — setActiveTab", () => {
  it("changes to matrix tab", () => {
    useNavigationStore.getState().setActiveTab("matrix");
    expect(useNavigationStore.getState().activeTab).toBe("matrix");
  });

  it("changes to dags tab", () => {
    useNavigationStore.getState().setActiveTab("dags");
    expect(useNavigationStore.getState().activeTab).toBe("dags");
  });

  it("changes to bouncers tab", () => {
    useNavigationStore.getState().setActiveTab("bouncers");
    expect(useNavigationStore.getState().activeTab).toBe("bouncers");
  });

  it("changes to ai tab", () => {
    useNavigationStore.getState().setActiveTab("ai");
    expect(useNavigationStore.getState().activeTab).toBe("ai");
  });

  it("changes to admin tab", () => {
    useNavigationStore.getState().setActiveTab("admin");
    expect(useNavigationStore.getState().activeTab).toBe("admin");
  });

  it("returns to catalog tab after switching away", () => {
    useNavigationStore.getState().setActiveTab("ai");
    useNavigationStore.getState().setActiveTab("catalog");
    expect(useNavigationStore.getState().activeTab).toBe("catalog");
  });

  it("accepts all valid TabType values", () => {
    const tabs: TabType[] = ["catalog", "matrix", "dags", "bouncers", "ai", "admin"];
    for (const tab of tabs) {
      useNavigationStore.getState().setActiveTab(tab);
      expect(useNavigationStore.getState().activeTab).toBe(tab);
    }
  });
});
