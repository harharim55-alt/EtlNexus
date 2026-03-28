import { lazy, Suspense, useEffect, useRef } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useNavigationStore, parseHash } from "@/stores/navigation-store";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useRunSelectorStore } from "@/stores/run-selector-store";
import { useAuthStore } from "@/stores/auth-store";
import { useComparisonStore } from "@/stores/comparison-store";
import { isAdmin } from "@/lib/permissions";
import { PipelineRegistry } from "@/components/pipeline-registry/PipelineRegistry";
import { Skeleton } from "@/components/ui/skeleton";
import { AuthBootstrap } from "@/components/auth/AuthProvider";
import { OnboardingOverlay } from "@/components/onboarding/OnboardingOverlay";
import { CommandPalette } from "@/components/shared/CommandPalette";
import { Breadcrumbs } from "@/components/layout/Breadcrumbs";

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
const BouncersView = lazy(() =>
  import("@/components/bouncers/BouncersView").then((m) => ({
    default: m.BouncersView,
  }))
);
const AIArchitectView = lazy(() =>
  import("@/components/ai-terminal/AIArchitectView").then((m) => ({
    default: m.AIArchitectView,
  }))
);
const AdminView = lazy(() =>
  import("@/components/admin/AdminView").then((m) => ({
    default: m.AdminView,
  }))
);
const ComparisonView = lazy(() =>
  import("@/components/comparison/ComparisonView").then((m) => ({
    default: m.ComparisonView,
  }))
);

function TabSkeleton() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <Skeleton className="h-64 w-96 bg-white/5 rounded-2xl" />
    </div>
  );
}

function AppContent() {
  const activeTab = useNavigationStore((s) => s.activeTab);
  const setActiveTab = useNavigationStore((s) => s.setActiveTab);
  const user = useAuthStore((s) => s.user);
  const isComparing = useComparisonStore((s) => s.isComparing);
  const initialHashApplied = useRef(false);

  // Apply deep link from initial URL hash on mount
  useEffect(() => {
    if (initialHashApplied.current) return;
    initialHashApplied.current = true;
    const { tab, pipelineId } = parseHash();
    if (tab === "catalog" && pipelineId) {
      usePipelineStore.getState().setSelectedPipelineId(pipelineId);
    }
  }, []);

  useEffect(() => {
    const onHashChange = () => {
      const { tab, pipelineId, dagRunId } = parseHash();
      if (tab !== activeTab) setActiveTab(tab);
      // Sync pipeline selection from URL (e.g. browser back/forward)
      const currentPipelineId = usePipelineStore.getState().selectedPipelineId;
      if (tab === "catalog") {
        if (pipelineId && pipelineId !== currentPipelineId) {
          usePipelineStore.getState().setSelectedPipelineId(pipelineId);
        } else if (!pipelineId && currentPipelineId) {
          usePipelineStore.getState().setSelectedPipelineId(null);
        }
        // Sync run selection from URL
        const currentRunId = useRunSelectorStore.getState().selectedDagRunId;
        if (dagRunId && dagRunId !== currentRunId) {
          // Minimal selectRun — full metadata will load from the API
          useRunSelectorStore.getState().selectRun(dagRunId, "", null, "");
        } else if (!dagRunId && currentRunId) {
          useRunSelectorStore.getState().clearRun();
        }
      }
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [activeTab, setActiveTab]);

  return (
    <>
      <AppShell>
        <div className="flex flex-col h-full">
          <Breadcrumbs />
          <div className="flex flex-1 min-h-0">
            {activeTab === "catalog" && !isComparing && (
              <>
                <PipelineRegistry />
                <Suspense fallback={<TabSkeleton />}>
                  <BentoWorkspace />
                </Suspense>
              </>
            )}
            {activeTab === "catalog" && isComparing && (
              <>
                <PipelineRegistry />
                <Suspense fallback={<TabSkeleton />}>
                  <ComparisonView />
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
            {activeTab === "bouncers" && (
              <Suspense fallback={<TabSkeleton />}>
                <BouncersView />
              </Suspense>
            )}
            {activeTab === "ai" && (
              <Suspense fallback={<TabSkeleton />}>
                <AIArchitectView />
              </Suspense>
            )}
            {activeTab === "admin" && isAdmin(user) && (
              <Suspense fallback={<TabSkeleton />}>
                <AdminView />
              </Suspense>
            )}
          </div>
        </div>
      </AppShell>
      <CommandPalette />
      <OnboardingOverlay />
    </>
  );
}

function App() {
  return (
    <AuthBootstrap>
      <AppContent />
    </AuthBootstrap>
  );
}

export default App;
