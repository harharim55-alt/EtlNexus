import { lazy, Suspense, useEffect } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useNavigationStore, getTabFromHash } from "@/stores/navigation-store";
import { useAuthStore } from "@/stores/auth-store";
import { isAdmin } from "@/lib/permissions";
import { PipelineRegistry } from "@/components/pipeline-registry/PipelineRegistry";
import { Skeleton } from "@/components/ui/skeleton";
import { AuthBootstrap } from "@/components/auth/AuthProvider";
import { OnboardingOverlay } from "@/components/onboarding/OnboardingOverlay";

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

  useEffect(() => {
    const onHashChange = () => {
      const tab = getTabFromHash();
      if (tab !== activeTab) setActiveTab(tab);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [activeTab, setActiveTab]);

  return (
    <>
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
      </AppShell>
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
