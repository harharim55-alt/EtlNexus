import { lazy, Suspense } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useNavigationStore } from "@/stores/navigation-store";
import { PipelineRegistry } from "@/components/pipeline-registry/PipelineRegistry";
import { Skeleton } from "@/components/ui/skeleton";

const BentoWorkspace = lazy(() =>
  import("@/components/bento-workspace/BentoWorkspace").then((m) => ({
    default: m.BentoWorkspace,
  }))
);
const SchemaMatrixView = lazy(() =>
  import("@/components/schema-matrix/SchemaMatrixView").then((m) => ({
    default: m.SchemaMatrixView,
  }))
);
const DagSummaryView = lazy(() =>
  import("@/components/dag-summary/DagSummaryView").then((m) => ({
    default: m.DagSummaryView,
  }))
);
const SensorsView = lazy(() =>
  import("@/components/sensors/SensorsView").then((m) => ({
    default: m.SensorsView,
  }))
);
const AIArchitectView = lazy(() =>
  import("@/components/ai-terminal/AIArchitectView").then((m) => ({
    default: m.AIArchitectView,
  }))
);

function TabSkeleton() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <Skeleton className="h-64 w-96 bg-white/5 rounded-2xl" />
    </div>
  );
}

function App() {
  const activeTab = useNavigationStore((s) => s.activeTab);

  return (
    <AppShell>
      <div className="flex h-full">
        {activeTab === "catalog" && (
          <>
            <PipelineRegistry />
            <Suspense fallback={<TabSkeleton />}>
              <BentoWorkspace />
            </Suspense>
          </>
        )}
        {activeTab === "matrix" && (
          <Suspense fallback={<TabSkeleton />}>
            <SchemaMatrixView />
          </Suspense>
        )}
        {activeTab === "dags" && (
          <Suspense fallback={<TabSkeleton />}>
            <DagSummaryView />
          </Suspense>
        )}
        {activeTab === "sensors" && (
          <Suspense fallback={<TabSkeleton />}>
            <SensorsView />
          </Suspense>
        )}
        {activeTab === "ai" && (
          <Suspense fallback={<TabSkeleton />}>
            <AIArchitectView />
          </Suspense>
        )}
      </div>
    </AppShell>
  );
}

export default App;
