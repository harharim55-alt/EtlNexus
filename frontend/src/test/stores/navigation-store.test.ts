import { describe, it, expect, beforeEach } from "vitest";
import { useNavigationStore } from "@/stores/navigation-store";
import type { TabType } from "@/lib/constants";

beforeEach(() => {
  useNavigationStore.setState({ activeTab: "data-products" });
});

describe("useNavigationStore — setActiveTab", () => {
  it("changes to matrix tab", () => {
    useNavigationStore.getState().setActiveTab("matrix");
    expect(useNavigationStore.getState().activeTab).toBe("matrix");
  });

  it("changes to ai tab", () => {
    useNavigationStore.getState().setActiveTab("ai");
    expect(useNavigationStore.getState().activeTab).toBe("ai");
  });

  it("changes to admin tab", () => {
    useNavigationStore.getState().setActiveTab("admin");
    expect(useNavigationStore.getState().activeTab).toBe("admin");
  });

  it("returns to data-products after switching away", () => {
    useNavigationStore.getState().setActiveTab("ai");
    useNavigationStore.getState().setActiveTab("data-products");
    expect(useNavigationStore.getState().activeTab).toBe("data-products");
  });

  it("accepts all valid TabType values", () => {
    const tabs: TabType[] = ["data-products", "matrix", "ai", "admin"];
    for (const tab of tabs) {
      useNavigationStore.getState().setActiveTab(tab);
      expect(useNavigationStore.getState().activeTab).toBe(tab);
    }
  });
});
