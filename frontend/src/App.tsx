import { lazy, Suspense, useEffect } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useNavigationStore, parseHash } from "@/stores/navigation-store";
import { useAuthStore } from "@/stores/auth-store";
import { canManageAccess } from "@/lib/permissions";
import { DataProductRegistry } from "@/components/data-products/DataProductRegistry";
import { Skeleton } from "@/components/ui/skeleton";
import { AuthBootstrap } from "@/components/auth/AuthProvider";
import { OnboardingOverlay } from "@/components/onboarding/OnboardingOverlay";
import { CommandPalette } from "@/components/shared/CommandPalette";

const SchemaMatrixView = lazy(() =>
  import("@/components/schema-matrix/SchemaMatrixView").then((m) => ({
    default: m.SchemaMatrixView,
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
const DataProductWorkspace = lazy(() =>
  import("@/components/data-products/DataProductWorkspace").then((m) => ({
    default: m.DataProductWorkspace,
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

  // Keep the active tab in sync with the URL hash (browser back/forward)
  useEffect(() => {
    const onHashChange = () => {
      const { tab } = parseHash();
      if (tab !== activeTab) setActiveTab(tab);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [activeTab, setActiveTab]);

  return (
    <>
      <AppShell>
        <div className="flex flex-col h-full">
          <div className="flex flex-1 min-h-0">
            {activeTab === "data-products" && (
              <>
                <DataProductRegistry />
                <Suspense fallback={<TabSkeleton />}>
                  <DataProductWorkspace />
                </Suspense>
              </>
            )}
            {activeTab === "matrix" && (
              <Suspense fallback={<TabSkeleton />}>
                <SchemaMatrixView />
              </Suspense>
            )}
            {activeTab === "ai" && (
              <Suspense fallback={<TabSkeleton />}>
                <AIArchitectView />
              </Suspense>
            )}
            {activeTab === "admin" && canManageAccess(user) && (
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
