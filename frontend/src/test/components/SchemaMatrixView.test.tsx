import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SchemaMatrixView } from "@/components/schema-matrix/SchemaMatrixView";
import type { SchemaMatrixResponse } from "@/types/schema-matrix";

// ── Mock heavy dependencies ─────────────────────────────────────────────────

vi.mock("@/hooks/use-schema-matrix", () => ({
  useSchemaMatrix: vi.fn(),
}));

// useVirtualizer requires real DOM measurement — mock to just render all items
vi.mock("@tanstack/react-virtual", () => ({
  useVirtualizer: vi.fn((opts: { count: number; estimateSize: () => number }) => ({
    getVirtualItems: () =>
      Array.from({ length: opts.count }, (_, i) => ({
        index: i,
        start: i * opts.estimateSize(),
        size: opts.estimateSize(),
        key: i,
        lane: 0,
        end: (i + 1) * opts.estimateSize(),
      })),
    getTotalSize: () => opts.count * opts.estimateSize(),
    measureElement: vi.fn(),
  })),
}));

// Mock FieldFrequencyRow to keep tests focused on SchemaMatrixView logic
vi.mock("@/components/schema-matrix/FieldFrequencyRow", () => ({
  FieldFrequencyRow: ({ row }: { row: { field_name: string } }) => (
    <div data-testid="field-row">{row.field_name}</div>
  ),
}));

import { useSchemaMatrix } from "@/hooks/use-schema-matrix";

const mockUseSchemaMatrix = vi.mocked(useSchemaMatrix);

function makeMatrixReturn(overrides: Partial<ReturnType<typeof useSchemaMatrix>> = {}): ReturnType<typeof useSchemaMatrix> {
  return {
    data: undefined,
    fetchNextPage: vi.fn(),
    hasNextPage: false,
    isFetchingNextPage: false,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  } as ReturnType<typeof useSchemaMatrix>;
}

function makePageData(fields: SchemaMatrixResponse["fields"], total = fields.length) {
  return {
    pages: [{ fields, total }],
    pageParams: [0],
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("SchemaMatrixView — loading state", () => {
  it("shows loading indicator while data is loading", () => {
    mockUseSchemaMatrix.mockReturnValue(
      makeMatrixReturn({ isLoading: true }),
    );
    render(<SchemaMatrixView />);
    expect(screen.getByText(/Initializing Registry/i)).toBeInTheDocument();
  });

  it("does not show the field matrix header during loading", () => {
    mockUseSchemaMatrix.mockReturnValue(
      makeMatrixReturn({ isLoading: true }),
    );
    render(<SchemaMatrixView />);
    expect(screen.queryByText(/Field Frequency Matrix/i)).not.toBeInTheDocument();
  });
});

describe("SchemaMatrixView — error state", () => {
  it("shows error message when the query fails", () => {
    mockUseSchemaMatrix.mockReturnValue(
      makeMatrixReturn({
        error: new Error("Network error"),
        isLoading: false,
      }),
    );
    render(<SchemaMatrixView />);
    expect(screen.getByText("Failed to load schema matrix")).toBeInTheDocument();
  });

  it("renders a Retry button on error", () => {
    const refetch = vi.fn();
    mockUseSchemaMatrix.mockReturnValue(
      makeMatrixReturn({
        error: new Error("Timeout"),
        isLoading: false,
        refetch,
      }),
    );
    render(<SchemaMatrixView />);
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("calls refetch when Retry button is clicked", () => {
    const refetch = vi.fn();
    mockUseSchemaMatrix.mockReturnValue(
      makeMatrixReturn({
        error: new Error("Timeout"),
        isLoading: false,
        refetch,
      }),
    );
    render(<SchemaMatrixView />);
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });
});

describe("SchemaMatrixView — empty state", () => {
  it("shows empty state when fields array is empty", () => {
    mockUseSchemaMatrix.mockReturnValue(
      makeMatrixReturn({
        data: makePageData([]),
        isLoading: false,
      }),
    );
    render(<SchemaMatrixView />);
    expect(screen.getByText(/No shared fields found across pipelines/i)).toBeInTheDocument();
  });
});

describe("SchemaMatrixView — data loaded state", () => {
  it("renders the Field Frequency Matrix header", () => {
    mockUseSchemaMatrix.mockReturnValue(
      makeMatrixReturn({
        data: makePageData([
          { field_name: "router_id", frequency: 5, pipelines: [] },
          { field_name: "ip_address", frequency: 3, pipelines: [] },
        ]),
        isLoading: false,
      }),
    );
    render(<SchemaMatrixView />);
    expect(screen.getByText("Field Frequency Matrix")).toBeInTheDocument();
  });

  it("shows the total field count in the subtitle", () => {
    mockUseSchemaMatrix.mockReturnValue(
      makeMatrixReturn({
        data: makePageData(
          [
            { field_name: "router_id", frequency: 5, pipelines: [] },
            { field_name: "ip_address", frequency: 3, pipelines: [] },
          ],
          42,
        ),
        isLoading: false,
      }),
    );
    render(<SchemaMatrixView />);
    expect(screen.getByText(/42 fields found/i)).toBeInTheDocument();
  });

  it("renders a FieldFrequencyRow for each field", () => {
    mockUseSchemaMatrix.mockReturnValue(
      makeMatrixReturn({
        data: makePageData([
          { field_name: "router_id", frequency: 5, pipelines: [] },
          { field_name: "ip_address", frequency: 3, pipelines: [] },
          { field_name: "bandwidth_mbps", frequency: 2, pipelines: [] },
        ]),
        isLoading: false,
      }),
    );
    render(<SchemaMatrixView />);
    const rows = screen.getAllByTestId("field-row");
    expect(rows).toHaveLength(3);
  });

  it("renders each field name via FieldFrequencyRow", () => {
    mockUseSchemaMatrix.mockReturnValue(
      makeMatrixReturn({
        data: makePageData([
          { field_name: "router_id", frequency: 5, pipelines: [] },
          { field_name: "ip_address", frequency: 3, pipelines: [] },
        ]),
        isLoading: false,
      }),
    );
    render(<SchemaMatrixView />);
    expect(screen.getByText("router_id")).toBeInTheDocument();
    expect(screen.getByText("ip_address")).toBeInTheDocument();
  });

  it("renders column headers: Field Name, Frequency, Pipelines", () => {
    mockUseSchemaMatrix.mockReturnValue(
      makeMatrixReturn({
        data: makePageData([{ field_name: "router_id", frequency: 5, pipelines: [] }]),
        isLoading: false,
      }),
    );
    render(<SchemaMatrixView />);
    // Use exact text match for column headers to avoid matching "Field Frequency Matrix"
    expect(screen.getByText("Field Name")).toBeInTheDocument();
    expect(screen.getByText("Frequency")).toBeInTheDocument();
    expect(screen.getByText("Pipelines")).toBeInTheDocument();
  });
});
