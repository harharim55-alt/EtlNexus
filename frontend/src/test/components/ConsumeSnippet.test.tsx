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
    render(<ConsumeSnippet pipelineName="SwitchPortCollector" category="Network Infrastructure" />);
    expect(screen.getByText(/Import & Consume/i)).toBeInTheDocument();
  });

  it("shows Catalog import from etls for a non-API category", () => {
    const { container } = render(<ConsumeSnippet pipelineName="SwitchPortCollector" category="Network Infrastructure" />);
    // "from" and "etls" are inside separate span/text nodes inside a <code> element
    const codeEl = container.querySelector("code");
    expect(codeEl).not.toBeNull();
    expect(codeEl!.textContent).toContain("from");
    expect(codeEl!.textContent).toContain("etls");
  });

  it("renders the lowercase pipeline name derived from the ETL name", () => {
    render(<ConsumeSnippet pipelineName="SwitchPortCollector" category="Network Infrastructure" />);
    // The importName is pipelineName.toLowerCase().replace(/ /g, "_")
    const elements = screen.getAllByText("switchportcollector");
    expect(elements.length).toBeGreaterThan(0);
  });

  it("renders consume().as_pyspark() call in the snippet", () => {
    render(<ConsumeSnippet pipelineName="SwitchPortCollector" />);
    expect(screen.getByText(/consume\(\)\.as_pyspark\(\)/)).toBeInTheDocument();
  });

  it("contains a copy button", () => {
    render(<ConsumeSnippet pipelineName="SwitchPortCollector" />);
    // CopyButton renders a button element
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("renders without category prop (defaults to ETL snippet)", () => {
    render(<ConsumeSnippet pipelineName="DnsQueryCollector" />);
    expect(screen.getByText(/consume\(\)\.as_pyspark\(\)/)).toBeInTheDocument();
  });
});

describe("ConsumeSnippet — API snippet", () => {
  it("renders 'from' keyword for API category", () => {
    render(<ConsumeSnippet pipelineName="NetworkInsightsApi" category="Network APIs" />);
    expect(screen.getByText("from")).toBeInTheDocument();
  });

  it("renders 'path' in the API snippet", () => {
    const { container } = render(<ConsumeSnippet pipelineName="NetworkInsightsApi" category="Network APIs" />);
    const codeEl = container.querySelector("code");
    expect(codeEl).not.toBeNull();
    expect(codeEl!.textContent).toContain("path");
  });

  it("renders 'api' import text for API category", () => {
    const { container } = render(<ConsumeSnippet pipelineName="NetworkInsightsApi" category="Network APIs" />);
    const codeEl = container.querySelector("code");
    expect(codeEl).not.toBeNull();
    expect(codeEl!.textContent).toContain("api");
  });

  it("does NOT render iceberg/catalog snippet for API category", () => {
    render(<ConsumeSnippet pipelineName="NetworkInsightsApi" category="Network APIs" />);
    expect(screen.queryByText(/iceberg/)).not.toBeInTheDocument();
  });

  it("renders lowercase pipeline name in the API snippet", () => {
    render(<ConsumeSnippet pipelineName="NetworkInsightsApi" category="Network APIs" />);
    const elements = screen.getAllByText("networkinsightsapi");
    expect(elements.length).toBeGreaterThan(0);
  });

  it("contains a copy button for API snippet", () => {
    render(<ConsumeSnippet pipelineName="NetworkInsightsApi" category="Network APIs" />);
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
  });
});
