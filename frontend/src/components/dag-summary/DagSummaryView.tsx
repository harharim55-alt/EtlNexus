import { useCallback } from "react";
import { BarChart3, Download } from "lucide-react";
import { useDagSummary } from "@/hooks/use-dag-summary";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { DateRangePicker } from "@/components/shared/DateRangePicker";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { downloadAsCSV } from "@/lib/export";
import { AggregateBar } from "./AggregateBar";
import { ExecutiveSummary } from "./ExecutiveSummary";
import { DagCard } from "./DagCard";
import { formatRelativeTime } from "@/lib/format";

export function DagSummaryView() {
  const { data, isLoading, error, refetch, dataUpdatedAt } = useDagSummary();

  const handleExportCSV = useCallback(() => {
    if (!data) return;
    const rows = data.dags.map((dag) => ({
      dag_id: dag.dag_id,
      task_count: dag.task_count,
      pipeline_count: dag.pipeline_count,
      success_rate: dag.success_rate,
      total_duration_seconds: dag.total_duration_seconds,
      latest_run_start: dag.latest_run_start,
    }));
    downloadAsCSV(rows, "dag-summary");
  }, [data]);

  if (isLoading) {
    return (
      <div data-section="dag-dashboard" className="flex-1 flex items-center justify-center">
        <LoadingState />
      </div>
    );
  }

  if (error) {
    return (
      <div data-section="dag-dashboard" className="flex-1 flex items-center justify-center">
        <ErrorState message="Failed to load DAG summary" onRetry={refetch} />
      </div>
    );
  }

  if (!data || data.dags.length === 0) {
    return (
      <div data-section="dag-dashboard" className="flex-1 flex items-center justify-center">
        <EmptyState message="No DAGs found" />
      </div>
    );
  }

  return (
    <div data-section="dag-dashboard" className="flex-1 overflow-y-auto custom-scrollbar">
      <div className="p-8 max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className="bg-indigo-500/10 p-2 rounded-lg border border-indigo-500/20">
                <BarChart3 className="w-5 h-5 text-indigo-400" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-foreground">
                  DAG Operations Dashboard
                </h1>
                <p className="text-xs text-text-muted font-mono mt-0.5">
                  {data.aggregate.total_dags} DAGs monitored &middot;{" "}
                  {data.aggregate.total_pipelines} pipelines
                  {dataUpdatedAt > 0 && (
                    <>
                      {" "}&middot; updated{" "}
                      {formatRelativeTime(new Date(dataUpdatedAt).toISOString())}
                    </>
                  )}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Tooltip>
                <TooltipTrigger
                  className="p-1.5 text-text-muted hover:text-foreground rounded-lg transition-colors cursor-pointer"
                  onClick={handleExportCSV}
                >
                  <Download className="size-4" />
                </TooltipTrigger>
                <TooltipContent>Export CSV</TooltipContent>
              </Tooltip>
              <DateRangePicker />
            </div>
          </div>
        </div>

        {/* Executive KPI Summary */}
        <div className="mb-6">
          <ExecutiveSummary aggregate={data.aggregate} dags={data.dags} />
        </div>

        {/* Aggregate Stats */}
        <div className="mb-8">
          <AggregateBar aggregate={data.aggregate} />
        </div>

        {/* DAG Cards Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {data.dags.map((dag) => (
            <DagCard key={dag.dag_id} dag={dag} />
          ))}
        </div>
      </div>
    </div>
  );
}
