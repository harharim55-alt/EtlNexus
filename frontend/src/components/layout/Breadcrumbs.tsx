import { ChevronRight } from "lucide-react";
import { useNavigationStore } from "@/stores/navigation-store";
import { usePipelineStore } from "@/stores/pipeline-store";
import { usePipelineDetail } from "@/hooks/use-pipeline-detail";
import type { TabType } from "@/lib/constants";

const TAB_LABELS: Record<TabType, string> = {
  catalog: "Catalog",
  matrix: "Field Matrix",
  dags: "DAG Summary",
  bouncers: "Bouncers",
  ai: "AI Architect",
  admin: "Access Control",
};

export function Breadcrumbs() {
  const activeTab = useNavigationStore((s) => s.activeTab);
  const breadcrumbs = useNavigationStore((s) => s.breadcrumbs);
  const popBreadcrumb = useNavigationStore((s) => s.popBreadcrumb);
  const selectedPipelineId = usePipelineStore((s) => s.selectedPipelineId);
  const setSelectedPipelineId = usePipelineStore((s) => s.setSelectedPipelineId);
  const { data: pipeline } = usePipelineDetail(selectedPipelineId);

  // Build the display trail: tab label + optional pipeline name from breadcrumbs or current selection
  const hasBreadcrumbTrail = breadcrumbs.length > 0;
  const hasCurrentPipeline = activeTab === "catalog" && selectedPipelineId && pipeline;

  // Only show when there's meaningful breadcrumb content
  if (!hasBreadcrumbTrail && !hasCurrentPipeline) return null;

  return (
    <div className="flex items-center gap-1 px-4 py-1.5 border-b border-border bg-background/50 shrink-0">
      {/* Tab root — always clickable to go back to the tab without a pipeline */}
      <button
        type="button"
        onClick={() => {
          if (activeTab === "catalog" && selectedPipelineId) {
            setSelectedPipelineId(null);
          }
          useNavigationStore.getState().clearBreadcrumbs();
        }}
        className="text-xs text-text-muted font-mono hover:text-foreground transition-colors cursor-pointer"
      >
        {TAB_LABELS[activeTab]}
      </button>

      {/* Breadcrumb history items (all clickable — they're previous pipelines) */}
      {breadcrumbs.map((crumb, idx) => (
        <span key={`${crumb.tab}-${crumb.pipelineId ?? idx}`} className="flex items-center gap-1">
          <ChevronRight className="w-3 h-3 text-text-muted/50 shrink-0" />
          <button
            type="button"
            onClick={() => {
              // Navigate back to this breadcrumb: keep items up to and including it
              const remaining = breadcrumbs.slice(0, idx + 1);
              const target = remaining[remaining.length - 1];
              useNavigationStore.setState({ breadcrumbs: remaining.slice(0, -1) });
              if (target?.pipelineId) {
                setSelectedPipelineId(target.pipelineId);
              }
            }}
            className="text-xs text-text-muted font-mono hover:text-foreground transition-colors cursor-pointer"
          >
            {crumb.label}
          </button>
        </span>
      ))}

      {/* Current pipeline name at the end of the trail */}
      {hasCurrentPipeline && (
        <>
          <ChevronRight className="w-3 h-3 text-text-muted/50 shrink-0" />
          <span className="text-xs text-foreground font-mono">{pipeline.name}</span>
        </>
      )}

      {/* Back button when there are breadcrumbs */}
      {hasBreadcrumbTrail && breadcrumbs.length > 1 && (
        <>
          <div className="w-px h-3 bg-hover-bg-strong mx-1.5" />
          <button
            type="button"
            onClick={popBreadcrumb}
            className="text-[10px] text-text-muted font-mono hover:text-foreground transition-colors cursor-pointer"
          >
            back
          </button>
        </>
      )}
    </div>
  );
}
