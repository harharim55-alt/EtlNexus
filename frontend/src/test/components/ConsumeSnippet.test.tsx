import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConsumeSnippet } from "@/components/bento-workspace/ConsumeSnippet";

// Mock navigator.clipboard to avoid jsdom limitations
beforeEach(() => {
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
    writable: true,
  });
});

describe("ConsumeSnippet — ETL (non-API) snippet", () => {
  it("renders Import & Consume header", () => {
    render(<ConsumeSnippet pipelineName="PortScanCollector" pipelineType="etl" team="Dagger" />);
    expect(screen.getByText(/Import & Consume/i)).toBeInTheDocument();
  });

  it("shows Catalog import from etls for a non-API pipeline", () => {
    const { container } = render(<ConsumeSnippet pipelineName="PortScanCollector" pipelineType="etl" team="Dagger" />);
    const codeEl = container.querySelector("code");
    expect(codeEl).not.toBeNull();
    expect(codeEl!.textContent).toContain("from");
    expect(codeEl!.textContent).toContain("etls");
  });

  it("renders the lowercase pipeline name derived from the ETL name", () => {
    render(<ConsumeSnippet pipelineName="PortScanCollector" pipelineType="etl" team="Dagger" />);
    const elements = screen.getAllByText("portscancollector");
    expect(elements.length).toBeGreaterThan(0);
  });

  it("renders consume().as_pyspark() call in the snippet", () => {
    render(<ConsumeSnippet pipelineName="PortScanCollector" team="Dagger" />);
    expect(screen.getByText(/consume\(\)\.as_pyspark\(\)/)).toBeInTheDocument();
  });

  it("contains a copy button", () => {
    render(<ConsumeSnippet pipelineName="PortScanCollector" team="Dagger" />);
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("renders without pipelineType prop (defaults to ETL snippet)", () => {
    render(<ConsumeSnippet pipelineName="DnsQueryCollector" team="Oasis" />);
    expect(screen.getByText(/consume\(\)\.as_pyspark\(\)/)).toBeInTheDocument();
  });
});

describe("ConsumeSnippet — API snippet", () => {
  it("renders 'from' keyword for API pipeline", () => {
    render(<ConsumeSnippet pipelineName="NetworkIntelApiDummy" pipelineType="api" team="Dagger" />);
    expect(screen.getByText("from")).toBeInTheDocument();
  });

  it("renders 'path' in the API snippet", () => {
    const { container } = render(<ConsumeSnippet pipelineName="NetworkIntelApiDummy" pipelineType="api" team="Dagger" />);
    const codeEl = container.querySelector("code");
    expect(codeEl).not.toBeNull();
    expect(codeEl!.textContent).toContain("path");
  });

  it("renders 'api' import text for API pipeline", () => {
    const { container } = render(<ConsumeSnippet pipelineName="NetworkIntelApiDummy" pipelineType="api" team="Dagger" />);
    const codeEl = container.querySelector("code");
    expect(codeEl).not.toBeNull();
    expect(codeEl!.textContent).toContain("api");
  });

  it("does NOT render iceberg/catalog snippet for API pipeline", () => {
    render(<ConsumeSnippet pipelineName="NetworkIntelApiDummy" pipelineType="api" team="Dagger" />);
    expect(screen.queryByText(/iceberg/)).not.toBeInTheDocument();
  });

  it("renders lowercase pipeline name in the API snippet", () => {
    render(<ConsumeSnippet pipelineName="NetworkIntelApiDummy" pipelineType="api" team="Dagger" />);
    const elements = screen.getAllByText("networkintelapidummy");
    expect(elements.length).toBeGreaterThan(0);
  });

  it("contains a copy button for API snippet", () => {
    render(<ConsumeSnippet pipelineName="NetworkIntelApiDummy" pipelineType="api" team="Dagger" />);
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
  });
});
