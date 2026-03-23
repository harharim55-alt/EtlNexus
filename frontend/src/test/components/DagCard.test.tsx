import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DagCard } from "@/components/dag-summary/DagCard";
import type { DagSummary } from "@/types/dag-summary";

// Mock the Tooltip components — they use Portal which requires real DOM positioning
vi.mock("@/components/ui/tooltip", () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children, className }: { children?: React.ReactNode; className?: string }) => (
    <span className={className}>{children}</span>
  ),
  TooltipContent: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

function makeDag(overrides: Partial<DagSummary> = {}): DagSummary {
  return {
    dag_id: "network_recon",
    description: null,
    schedule_interval: "@daily",
    is_paused: false,
    task_count: 10,
    pipeline_count: 5,
    total_duration_seconds: 3600,
    avg_task_duration_seconds: 120,
    min_task_duration_seconds: 60,
    max_task_duration_seconds: 300,
    status_counts: { success: 8, failed: 0 },
    success_rate: 100,
    latest_run_start: null,
    latest_run_end: null,
    typical_finish_hour: null,
    total_runs_30d: 30,
    dag_success_rate_30d: 100,
    tasks: [],
    ...overrides,
  };
}

describe("DagCard — DAG name formatting", () => {
  it("renders dag_id with underscores converted to title case words", () => {
    render(<DagCard dag={makeDag({ dag_id: "network_recon" })} />);
    expect(screen.getByText("Backbone Core")).toBeInTheDocument();
  });

  it("renders multi-word dag_id with each word capitalized", () => {
    render(<DagCard dag={makeDag({ dag_id: "traffic_analysis" })} />);
    expect(screen.getByText("Traffic Analysis")).toBeInTheDocument();
  });

  it("renders single word dag_id", () => {
    render(<DagCard dag={makeDag({ dag_id: "sentinel" })} />);
    expect(screen.getByText("Sentinel")).toBeInTheDocument();
  });
});

describe("DagCard — task and pipeline counts", () => {
  it("shows task count", () => {
    render(<DagCard dag={makeDag({ task_count: 12 })} />);
    expect(screen.getByText(/12 tasks/i)).toBeInTheDocument();
  });

  it("shows pipeline count", () => {
    render(<DagCard dag={makeDag({ pipeline_count: 7 })} />);
    expect(screen.getByText(/7 pipelines/i)).toBeInTheDocument();
  });
});

describe("DagCard — success rate", () => {
  it("shows success rate percentage", () => {
    render(<DagCard dag={makeDag({ success_rate: 85 })} />);
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("shows em-dash when success_rate is null", () => {
    render(<DagCard dag={makeDag({ success_rate: null })} />);
    // "—" appears in the success rate section
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThan(0);
  });
});

describe("DagCard — failed tasks button", () => {
  it("does not show failed tasks button when no failures", () => {
    render(<DagCard dag={makeDag({ status_counts: { success: 10 } })} />);
    expect(screen.queryByText(/failed/i)).not.toBeInTheDocument();
  });

  it("shows failed tasks button when there are failures", () => {
    render(
      <DagCard
        dag={makeDag({
          status_counts: { success: 7, failed: 2 },
          tasks: [
            {
              task_id: "FailTask1",
              pipeline_name: "SomePipeline",
              pipeline_id: "pid-1",
              status: "failed",
              latest_duration_seconds: 10,
              avg_duration_seconds: 10,
              task_group_id: null,
            },
            {
              task_id: "FailTask2",
              pipeline_name: "AnotherPipeline",
              pipeline_id: "pid-2",
              status: "failed",
              latest_duration_seconds: 20,
              avg_duration_seconds: 20,
              task_group_id: null,
            },
          ],
        })}
      />,
    );
    // The failed button is the only button in the card
    const failedBtn = screen.getByRole("button");
    expect(failedBtn).toBeInTheDocument();
    expect(failedBtn.textContent).toMatch(/2 failed/i);
  });

  it("toggles failed tasks panel when the failed button is clicked", () => {
    const dag = makeDag({
      status_counts: { success: 7, failed: 1 },
      tasks: [
        {
          task_id: "FailTask1",
          pipeline_name: "SomePipeline",
          pipeline_id: "pid-1",
          status: "failed",
          latest_duration_seconds: 10,
          avg_duration_seconds: 10,
          task_group_id: null,
        },
      ],
    });

    render(<DagCard dag={dag} />);

    const failedBtn = screen.getByRole("button");

    // Panel should not be visible initially
    expect(screen.queryByText(/1 Failed Tasks/i)).not.toBeInTheDocument();

    // Click the failed button to open the panel
    fireEvent.click(failedBtn);
    expect(screen.getByText(/1 Failed Tasks/i)).toBeInTheDocument();

    // Click again to close the panel
    fireEvent.click(failedBtn);
    expect(screen.queryByText(/1 Failed Tasks/i)).not.toBeInTheDocument();
  });

  it("shows failed task pipeline name in expanded panel", () => {
    const dag = makeDag({
      status_counts: { success: 5, failed: 1 },
      tasks: [
        {
          task_id: "FailTask1",
          pipeline_name: "PortScanCollector",
          pipeline_id: "pid-1",
          status: "failed",
          latest_duration_seconds: 30,
          avg_duration_seconds: 30,
          task_group_id: null,
        },
      ],
    });

    render(<DagCard dag={dag} />);
    fireEvent.click(screen.getByRole("button"));
    // pipeline_name appears in the panel row (may also appear in Tooltip content)
    const matches = screen.getAllByText("PortScanCollector");
    expect(matches.length).toBeGreaterThan(0);
  });
});

describe("DagCard — schedule", () => {
  it("shows schedule interval when provided", () => {
    render(<DagCard dag={makeDag({ schedule_interval: "@hourly" })} />);
    expect(screen.getByText("@hourly")).toBeInTheDocument();
  });

  it("does not show schedule section when schedule_interval is null", () => {
    render(<DagCard dag={makeDag({ schedule_interval: null })} />);
    expect(screen.queryByText("@hourly")).not.toBeInTheDocument();
  });
});

describe("DagCard — paused state", () => {
  it("shows Paused badge when is_paused is true", () => {
    render(<DagCard dag={makeDag({ is_paused: true })} />);
    expect(screen.getByText(/paused/i)).toBeInTheDocument();
  });

  it("does not show Paused badge when is_paused is false", () => {
    render(<DagCard dag={makeDag({ is_paused: false })} />);
    expect(screen.queryByText(/paused/i)).not.toBeInTheDocument();
  });
});
