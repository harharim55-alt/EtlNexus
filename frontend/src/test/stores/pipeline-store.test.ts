import { describe, it, expect, beforeEach } from "vitest";
import { usePipelineStore } from "@/stores/pipeline-store";

// Reset Zustand store state between tests
beforeEach(() => {
  usePipelineStore.setState({
    selectedPipelineId: null,
    selectedDagId: null,
    searchQuery: "",
    filtersOpen: false,
    teamFilters: new Set<string>(),
    dagFilters: new Set<string>(),
    statusFilters: new Set<string>(),
  });
});

describe("usePipelineStore — initial state", () => {
  it("has null selectedPipelineId", () => {
    expect(usePipelineStore.getState().selectedPipelineId).toBeNull();
  });

  it("has null selectedDagId", () => {
    expect(usePipelineStore.getState().selectedDagId).toBeNull();
  });

  it("has empty searchQuery", () => {
    expect(usePipelineStore.getState().searchQuery).toBe("");
  });

  it("has filtersOpen false", () => {
    expect(usePipelineStore.getState().filtersOpen).toBe(false);
  });

  it("has empty teamFilters", () => {
    expect(usePipelineStore.getState().teamFilters.size).toBe(0);
  });

  it("has empty dagFilters", () => {
    expect(usePipelineStore.getState().dagFilters.size).toBe(0);
  });

  it("has empty statusFilters", () => {
    expect(usePipelineStore.getState().statusFilters.size).toBe(0);
  });
});

describe("usePipelineStore — setSelectedPipelineId", () => {
  it("updates selectedPipelineId", () => {
    usePipelineStore.getState().setSelectedPipelineId("abc-123");
    expect(usePipelineStore.getState().selectedPipelineId).toBe("abc-123");
  });

  it("clears selectedDagId when a pipeline is selected", () => {
    usePipelineStore.setState({ selectedDagId: "some-dag" });
    usePipelineStore.getState().setSelectedPipelineId("abc-123");
    expect(usePipelineStore.getState().selectedDagId).toBeNull();
  });

  it("setting null clears selection", () => {
    usePipelineStore.setState({ selectedPipelineId: "abc-123" });
    usePipelineStore.getState().setSelectedPipelineId(null);
    expect(usePipelineStore.getState().selectedPipelineId).toBeNull();
  });
});

describe("usePipelineStore — setSearchQuery", () => {
  it("updates searchQuery", () => {
    usePipelineStore.getState().setSearchQuery("SwitchPort");
    expect(usePipelineStore.getState().searchQuery).toBe("SwitchPort");
  });

  it("clears searchQuery when set to empty string", () => {
    usePipelineStore.setState({ searchQuery: "hello" });
    usePipelineStore.getState().setSearchQuery("");
    expect(usePipelineStore.getState().searchQuery).toBe("");
  });
});

describe("usePipelineStore — setFiltersOpen", () => {
  it("opens filters", () => {
    usePipelineStore.getState().setFiltersOpen(true);
    expect(usePipelineStore.getState().filtersOpen).toBe(true);
  });

  it("closes filters", () => {
    usePipelineStore.setState({ filtersOpen: true });
    usePipelineStore.getState().setFiltersOpen(false);
    expect(usePipelineStore.getState().filtersOpen).toBe(false);
  });
});

describe("usePipelineStore — toggleFilter", () => {
  it("adds a team filter value", () => {
    usePipelineStore.getState().toggleFilter("team", "Dagger");
    expect(usePipelineStore.getState().teamFilters.has("Dagger")).toBe(true);
  });

  it("removes a team filter value that was already present", () => {
    usePipelineStore.getState().toggleFilter("team", "Dagger");
    usePipelineStore.getState().toggleFilter("team", "Dagger");
    expect(usePipelineStore.getState().teamFilters.has("Dagger")).toBe(false);
  });

  it("adds a dag filter value", () => {
    usePipelineStore.getState().toggleFilter("dag", "backbone_core");
    expect(usePipelineStore.getState().dagFilters.has("backbone_core")).toBe(true);
  });

  it("adds a status filter value", () => {
    usePipelineStore.getState().toggleFilter("status", "failed");
    expect(usePipelineStore.getState().statusFilters.has("failed")).toBe(true);
  });

  it("supports multiple independent filter values", () => {
    usePipelineStore.getState().toggleFilter("team", "Dagger");
    usePipelineStore.getState().toggleFilter("team", "Vault");
    const filters = usePipelineStore.getState().teamFilters;
    expect(filters.has("Dagger")).toBe(true);
    expect(filters.has("Vault")).toBe(true);
  });
});

describe("usePipelineStore — clearAllFilters", () => {
  it("resets all filter sets", () => {
    usePipelineStore.getState().toggleFilter("team", "Dagger");
    usePipelineStore.getState().toggleFilter("dag", "backbone_core");
    usePipelineStore.getState().toggleFilter("status", "failed");

    usePipelineStore.getState().clearAllFilters();

    expect(usePipelineStore.getState().teamFilters.size).toBe(0);
    expect(usePipelineStore.getState().dagFilters.size).toBe(0);
    expect(usePipelineStore.getState().statusFilters.size).toBe(0);
  });
});
