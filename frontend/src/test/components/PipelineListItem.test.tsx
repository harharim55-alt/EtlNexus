import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PipelineListItem } from "@/components/pipeline-registry/PipelineListItem";
import type { PipelineListItem as PipelineListItemType } from "@/types/pipeline";

function makePipeline(overrides: Partial<PipelineListItemType> = {}): PipelineListItemType {
  return {
    id: "pipeline-1",
    name: "PortScanCollector",
    description: "Collects switch port data",
    category: "Network Infrastructure",
    pipeline_type: "etl",
    schedule: "@daily",
    schedule_type: null,
    rows_per_day: "50K",
    airflow_status: "success",
    success_rate: 95,
    team: "Dagger",
    last_run_at: null,
    execution_date: null,
    tags: [],
    is_data_product: false,
    network_names: [],
    ...overrides,
  };
}

describe("PipelineListItem — rendering pipeline name", () => {
  it("renders the pipeline name", () => {
    render(
      <PipelineListItem
        pipeline={makePipeline()}
        isActive={false}
        onClick={vi.fn()}
      />,
    );
    expect(screen.getByText("PortScanCollector")).toBeInTheDocument();
  });

  it("shows ETL type label for etl pipeline_type", () => {
    render(
      <PipelineListItem
        pipeline={makePipeline({ pipeline_type: "etl" })}
        isActive={false}
        onClick={vi.fn()}
      />,
    );
    expect(screen.getByText("ETL")).toBeInTheDocument();
  });

  it("shows API type label for api pipeline_type", () => {
    render(
      <PipelineListItem
        pipeline={makePipeline({ pipeline_type: "api" })}
        isActive={false}
        onClick={vi.fn()}
      />,
    );
    expect(screen.getByText("API")).toBeInTheDocument();
  });
});

describe("PipelineListItem — success rate dot color", () => {
  it("renders emerald dot for success_rate >= 80", () => {
    const { container } = render(
      <PipelineListItem
        pipeline={makePipeline({ success_rate: 90 })}
        isActive={false}
        onClick={vi.fn()}
      />,
    );
    const dot = container.querySelector(".bg-emerald-500");
    expect(dot).toBeInTheDocument();
  });

  it("renders amber dot for success_rate between 50 and 79", () => {
    const { container } = render(
      <PipelineListItem
        pipeline={makePipeline({ success_rate: 65 })}
        isActive={false}
        onClick={vi.fn()}
      />,
    );
    const dot = container.querySelector(".bg-amber-500");
    expect(dot).toBeInTheDocument();
  });

  it("renders rose dot for success_rate below 50", () => {
    const { container } = render(
      <PipelineListItem
        pipeline={makePipeline({ success_rate: 30 })}
        isActive={false}
        onClick={vi.fn()}
      />,
    );
    const dot = container.querySelector(".bg-rose-500");
    expect(dot).toBeInTheDocument();
  });

  it("renders slate dot when success_rate is null", () => {
    const { container } = render(
      <PipelineListItem
        pipeline={makePipeline({ success_rate: null })}
        isActive={false}
        onClick={vi.fn()}
      />,
    );
    const dot = container.querySelector(".bg-slate-500");
    expect(dot).toBeInTheDocument();
  });
});

describe("PipelineListItem — schedule and rows pills", () => {
  it("shows schedule pill when schedule is provided", () => {
    render(
      <PipelineListItem
        pipeline={makePipeline({ schedule: "@hourly" })}
        isActive={false}
        onClick={vi.fn()}
      />,
    );
    expect(screen.getByText("@hourly")).toBeInTheDocument();
  });

  it("does not show schedule pill when schedule is null", () => {
    render(
      <PipelineListItem
        pipeline={makePipeline({ schedule: null })}
        isActive={false}
        onClick={vi.fn()}
      />,
    );
    expect(screen.queryByText("@daily")).not.toBeInTheDocument();
  });

  it("shows rows_per_day pill when provided", () => {
    render(
      <PipelineListItem
        pipeline={makePipeline({ rows_per_day: "100K" })}
        isActive={false}
        onClick={vi.fn()}
      />,
    );
    expect(screen.getByText("100K")).toBeInTheDocument();
  });

  it("does not show rows_per_day pill when null", () => {
    render(
      <PipelineListItem
        pipeline={makePipeline({ rows_per_day: null })}
        isActive={false}
        onClick={vi.fn()}
      />,
    );
    expect(screen.queryByText(/K$/)).not.toBeInTheDocument();
  });
});

describe("PipelineListItem — click interaction", () => {
  it("calls onClick when the item is clicked", () => {
    const onClick = vi.fn();
    render(
      <PipelineListItem
        pipeline={makePipeline()}
        isActive={false}
        onClick={onClick}
      />,
    );
    fireEvent.click(screen.getByText("PortScanCollector"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe("PipelineListItem — active state styles", () => {
  it("applies indigo border class when isActive is true", () => {
    const { container } = render(
      <PipelineListItem
        pipeline={makePipeline()}
        isActive={true}
        onClick={vi.fn()}
      />,
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("border-indigo-500/30");
  });

  it("does not apply indigo border when isActive is false", () => {
    const { container } = render(
      <PipelineListItem
        pipeline={makePipeline()}
        isActive={false}
        onClick={vi.fn()}
      />,
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).not.toContain("border-indigo-500/30");
  });

  it("applies indigo text color to name when isActive is true", () => {
    render(
      <PipelineListItem
        pipeline={makePipeline()}
        isActive={true}
        onClick={vi.fn()}
      />,
    );
    const nameEl = screen.getByText("PortScanCollector");
    expect(nameEl.className).toContain("text-indigo-400");
  });

  it("applies slate text color to name when isActive is false", () => {
    render(
      <PipelineListItem
        pipeline={makePipeline()}
        isActive={false}
        onClick={vi.fn()}
      />,
    );
    const nameEl = screen.getByText("PortScanCollector");
    expect(nameEl.className).toContain("text-slate-200");
  });
});
