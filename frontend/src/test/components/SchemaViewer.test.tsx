import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SchemaViewer } from "@/components/bento-workspace/SchemaViewer";
import type { PipelineField } from "@/types/pipeline";

function makeField(overrides: Partial<PipelineField> & { id: string; name: string }): PipelineField {
  return {
    data_type: "VARCHAR",
    ordinal_position: 1,
    ...overrides,
  };
}

describe("SchemaViewer — field names", () => {
  it("renders a field name", () => {
    render(
      <SchemaViewer
        fields={[makeField({ id: "f1", name: "switch_port_id" })]}
      />,
    );
    expect(screen.getByText("switch_port_id")).toBeInTheDocument();
  });

  it("renders multiple field names", () => {
    render(
      <SchemaViewer
        fields={[
          makeField({ id: "f1", name: "router_id", ordinal_position: 1 }),
          makeField({ id: "f2", name: "ip_address", ordinal_position: 2 }),
          makeField({ id: "f3", name: "bandwidth_mbps", ordinal_position: 3 }),
        ]}
      />,
    );
    expect(screen.getByText("router_id")).toBeInTheDocument();
    expect(screen.getByText("ip_address")).toBeInTheDocument();
    expect(screen.getByText("bandwidth_mbps")).toBeInTheDocument();
  });
});

describe("SchemaViewer — data types", () => {
  it("renders explicit data_type when provided", () => {
    render(
      <SchemaViewer
        fields={[makeField({ id: "f1", name: "created_at", data_type: "TIMESTAMP" })]}
      />,
    );
    expect(screen.getByText("TIMESTAMP")).toBeInTheDocument();
  });

  it("infers UUID type from field name containing 'id' when data_type is null", () => {
    render(
      <SchemaViewer
        fields={[makeField({ id: "f1", name: "router_id", data_type: null })]}
      />,
    );
    expect(screen.getByText("UUID")).toBeInTheDocument();
  });

  it("infers TIMESTAMP from field name containing 'date' when data_type is null", () => {
    render(
      <SchemaViewer
        fields={[makeField({ id: "f1", name: "collection_date", data_type: null })]}
      />,
    );
    expect(screen.getByText("TIMESTAMP")).toBeInTheDocument();
  });

  it("infers BOOL from field name starting with 'is_' when data_type is null", () => {
    render(
      <SchemaViewer
        fields={[makeField({ id: "f1", name: "is_active", data_type: null })]}
      />,
    );
    expect(screen.getByText("BOOL")).toBeInTheDocument();
  });

  it("infers VARCHAR as fallback when data_type is null and name has no special pattern", () => {
    render(
      <SchemaViewer
        fields={[makeField({ id: "f1", name: "description", data_type: null })]}
      />,
    );
    expect(screen.getByText("VARCHAR")).toBeInTheDocument();
  });

  it("shows provided data_type even if name contains 'id'", () => {
    render(
      <SchemaViewer
        fields={[makeField({ id: "f1", name: "router_id", data_type: "INT4" })]}
      />,
    );
    expect(screen.getByText("INT4")).toBeInTheDocument();
  });
});

describe("SchemaViewer — empty state", () => {
  it("shows 'No fields defined' when fields array is empty", () => {
    render(<SchemaViewer fields={[]} />);
    expect(screen.getByText("No fields defined")).toBeInTheDocument();
  });

  it("does not show 'No fields defined' when fields are present", () => {
    render(
      <SchemaViewer
        fields={[makeField({ id: "f1", name: "switch_port_id" })]}
      />,
    );
    expect(screen.queryByText("No fields defined")).not.toBeInTheDocument();
  });
});

describe("SchemaViewer — section header", () => {
  it("renders 'Data Structure' header", () => {
    render(<SchemaViewer fields={[]} />);
    expect(screen.getByText(/Data Structure/i)).toBeInTheDocument();
  });
});
