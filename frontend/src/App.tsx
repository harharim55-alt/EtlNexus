import { lazy, Suspense, useEffect } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useNavigationStore, parseHash } from "@/stores/navigation-store";
import { DataProductRegistry } from "@/components/data-products/DataProductRegistry";
import { Skeleton } from "@/components/ui/skeleton";
import { AuthBootstrap } from "@/components/auth/AuthProvider";
import { OnboardingOverlay } from "@/components/onboarding/OnboardingOverlay";
import { CommandPalette } from "@/components/shared/CommandPalette";

const TablesView = lazy(() =>
  import("@/components/tables/TablesView").then((m) => ({
    default: m.TablesView,
  }))
);
const AIArchitectView = lazy(() =>
  import("@/components/ai-terminal/AIArchitectView").then((m) => ({
    default: m.AIArchitectView,
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
            {activeTab === "tables" && (
              <Suspense fallback={<TabSkeleton />}>
                <TablesView />
              </Suspense>
            )}
            {activeTab === "ai" && (
              <Suspense fallback={<TabSkeleton />}>
                <AIArchitectView />
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
