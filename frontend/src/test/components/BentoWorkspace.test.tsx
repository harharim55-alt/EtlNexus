import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { BentoWorkspace } from "@/components/bento-workspace/BentoWorkspace";
import type { PipelineDetail } from "@/types/pipeline";
import type { PipelineState } from "@/stores/pipeline-store";

// ── Mock all hooks and sub-components that reach outside ────────────────────

vi.mock("@/hooks/use-pipeline-detail", () => ({
  usePipelineDetail: vi.fn(),
}));

vi.mock("@/hooks/use-update-pipeline", () => ({
  useUpdatePipeline: vi.fn(),
}));

vi.mock("@/stores/pipeline-store", () => ({
  usePipelineStore: vi.fn(),
}));

// Mock every bento sub-component so we only test BentoWorkspace branching logic
vi.mock("@/components/bento-workspace/BentoHeader", () => ({
  BentoHeader: ({ pipeline }: { pipeline: PipelineDetail }) => (
    <div data-testid="bento-header">{pipeline.name}</div>
  ),
}));

vi.mock("@/components/bento-workspace/LineageTopology", () => ({
  LineageTopology: () => <div data-testid="lineage-topology" />,
}));

vi.mock("@/components/bento-workspace/MetricsCards", () => ({
  MetricsCards: () => <div data-testid="metrics-cards" />,
}));

vi.mock("@/components/bento-workspace/SchemaViewer", () => ({
  SchemaViewer: () => <div data-testid="schema-viewer" />,
}));

vi.mock("@/components/bento-workspace/ConsumeSnippet", () => ({
  ConsumeSnippet: () => <div data-testid="consume-snippet" />,
}));

vi.mock("@/components/bento-workspace/JoinIntelligence", () => ({
  JoinIntelligence: () => <div data-testid="join-intelligence" />,
}));

vi.mock("@/components/bento-workspace/UsageCard", () => ({
  UsageCard: () => <div data-testid="usage-card" />,
}));

vi.mock("@/components/bento-workspace/ResourcePerformanceCard", () => ({
  ResourcePerformanceCard: () => <div data-testid="resource-performance-card" />,
}));

vi.mock("@/components/bento-workspace/TransformInspectorCard", () => ({
  TransformInspectorCard: () => <div data-testid="transform-inspector-card" />,
}));

// ── Import after mocks are registered ──────────────────────────────────────

import { usePipelineDetail } from "@/hooks/use-pipeline-detail";
import { useUpdatePipeline } from "@/hooks/use-update-pipeline";
import { usePipelineStore } from "@/stores/pipeline-store";

const mockUsePipelineDetail = vi.mocked(usePipelineDetail);
const mockUseUpdatePipeline = vi.mocked(useUpdatePipeline);
const mockUsePipelineStore = vi.mocked(usePipelineStore);

// Helper: create a fully-typed PipelineState stub for the selector mock
function makeStoreSelector(selectedPipelineId: string | null) {
  return (selector: (state: PipelineState) => unknown) =>
    selector({
      selectedPipelineId,
      selectedDagId: null,
      searchQuery: "",
      filtersOpen: false,
      teamFilters: new Set<string>(),
      dagFilters: new Set<string>(),
      statusFilters: new Set<string>(),
      setSelectedPipelineId: vi.fn(),
      setSelectedDagId: vi.fn(),
      setSearchQuery: vi.fn(),
      setFiltersOpen: vi.fn(),
      toggleFilter: vi.fn(),
      clearAllFilters: vi.fn(),
    } as PipelineState);
}

function makePipelineDetail(overrides: Partial<PipelineDetail> = {}): PipelineDetail {
  return {
    id: "pipeline-1",
    name: "SwitchPortCollector",
    task_id: "SwitchPortCollector",
    description: "Collects switch port data",
    category: "Network Infrastructure",
    schedule: "@daily",
    rows_per_day: "50K",
    airflow_status: "success",
    fields: [],
    source_tables: [],
    destination_tables: [],
    documentation: null,
    last_updated_by: null,
    last_updated_at: null,
    created_at: null,
    updated_at: null,
    team: "Dagger",
    team_id: "team-1",
    can_edit: true,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();

  // Default: no pipeline selected
  mockUsePipelineStore.mockImplementation(makeStoreSelector(null));

  mockUseUpdatePipeline.mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useUpdatePipeline>);

  mockUsePipelineDetail.mockReturnValue({
    data: undefined,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof usePipelineDetail>);
});

describe("BentoWorkspace — no pipeline selected", () => {
  it("shows placeholder text when no pipeline is selected", () => {
    render(<BentoWorkspace />);
    expect(screen.getByText("Select a pipeline to explore")).toBeInTheDocument();
  });

  it("does not render BentoHeader when no pipeline selected", () => {
    render(<BentoWorkspace />);
    expect(screen.queryByTestId("bento-header")).not.toBeInTheDocument();
  });
});

describe("BentoWorkspace — loading state", () => {
  beforeEach(() => {
    mockUsePipelineStore.mockImplementation(makeStoreSelector("pipeline-1"));
    mockUsePipelineDetail.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof usePipelineDetail>);
  });

  it("renders skeleton elements when loading", () => {
    const { container } = render(<BentoWorkspace />);
    const skeletons = container.querySelectorAll("[data-slot='skeleton']");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("does not show placeholder text when loading", () => {
    render(<BentoWorkspace />);
    expect(screen.queryByText("Select a pipeline to explore")).not.toBeInTheDocument();
  });
});

describe("BentoWorkspace — error state", () => {
  beforeEach(() => {
    mockUsePipelineStore.mockImplementation(makeStoreSelector("pipeline-1"));
    mockUsePipelineDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed to fetch"),
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof usePipelineDetail>);
  });

  it("renders error state message when fetch fails", () => {
    render(<BentoWorkspace />);
    expect(screen.getByText("Failed to load pipeline details")).toBeInTheDocument();
  });

  it("renders Retry button on error", () => {
    render(<BentoWorkspace />);
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });
});

describe("BentoWorkspace — pipeline loaded", () => {
  beforeEach(() => {
    mockUsePipelineStore.mockImplementation(makeStoreSelector("pipeline-1"));
    mockUsePipelineDetail.mockReturnValue({
      data: makePipelineDetail(),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof usePipelineDetail>);
  });

  it("renders BentoHeader with pipeline name when data is loaded", () => {
    render(<BentoWorkspace />);
    expect(screen.getByTestId("bento-header")).toBeInTheDocument();
    expect(screen.getByText("SwitchPortCollector")).toBeInTheDocument();
  });

  it("renders schema viewer for loaded pipeline", () => {
    render(<BentoWorkspace />);
    expect(screen.getByTestId("schema-viewer")).toBeInTheDocument();
  });

  it("renders consume snippet for loaded pipeline", () => {
    render(<BentoWorkspace />);
    expect(screen.getByTestId("consume-snippet")).toBeInTheDocument();
  });

  it("renders resource performance card for non-API pipeline", () => {
    render(<BentoWorkspace />);
    expect(screen.getByTestId("resource-performance-card")).toBeInTheDocument();
  });

  it("does not render resource performance card for API category pipeline", () => {
    mockUsePipelineDetail.mockReturnValue({
      data: makePipelineDetail({ category: "Network APIs" }),
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof usePipelineDetail>);
    render(<BentoWorkspace />);
    expect(screen.queryByTestId("resource-performance-card")).not.toBeInTheDocument();
  });
});
