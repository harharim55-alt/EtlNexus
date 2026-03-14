import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricsCards } from "@/components/bento-workspace/MetricsCards";

describe("MetricsCards — schedule display", () => {
  it("renders the provided schedule value", () => {
    render(<MetricsCards rowsPerDay="50K" schedule="@daily" />);
    expect(screen.getByText("@daily")).toBeInTheDocument();
  });

  it("renders em-dash when schedule is null", () => {
    render(<MetricsCards rowsPerDay="50K" schedule={null} />);
    // The Schedule card renders "—" when null
    const dashes = screen.getAllByText("—");
    // At least one dash appears (either schedule or rowsPerDay or both)
    expect(dashes.length).toBeGreaterThan(0);
  });

  it("renders custom schedule string", () => {
    render(<MetricsCards rowsPerDay={null} schedule="Every 4 hours" />);
    expect(screen.getByText("Every 4 hours")).toBeInTheDocument();
  });
});

describe("MetricsCards — rows per day display", () => {
  it("renders the provided rowsPerDay value", () => {
    render(<MetricsCards rowsPerDay="120K" schedule="@daily" />);
    expect(screen.getByText("120K")).toBeInTheDocument();
  });

  it("renders em-dash when rowsPerDay is null", () => {
    render(<MetricsCards rowsPerDay={null} schedule="@daily" />);
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThan(0);
  });
});

describe("MetricsCards — section labels", () => {
  it("renders Volume Rate label", () => {
    render(<MetricsCards rowsPerDay="50K" schedule="@daily" />);
    expect(screen.getByText(/Volume Rate/i)).toBeInTheDocument();
  });

  it("renders Schedule label", () => {
    render(<MetricsCards rowsPerDay="50K" schedule="@daily" />);
    expect(screen.getByText(/Schedule/i)).toBeInTheDocument();
  });

  it("renders rows/day unit label", () => {
    render(<MetricsCards rowsPerDay="50K" schedule="@daily" />);
    expect(screen.getByText("rows/day")).toBeInTheDocument();
  });
});

describe("MetricsCards — handles both null values", () => {
  it("renders without crashing when both values are null", () => {
    expect(() => render(<MetricsCards rowsPerDay={null} schedule={null} />)).not.toThrow();
  });

  it("shows two em-dashes when both values are null", () => {
    render(<MetricsCards rowsPerDay={null} schedule={null} />);
    const dashes = screen.getAllByText("—");
    expect(dashes).toHaveLength(2);
  });
});
