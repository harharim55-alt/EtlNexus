import { AppShell } from "@/components/layout/AppShell";
import { useNavigationStore } from "@/stores/navigation-store";
import { PipelineRegistry } from "@/components/pipeline-registry/PipelineRegistry";
import { BentoWorkspace } from "@/components/bento-workspace/BentoWorkspace";
import { SchemaMatrixView } from "@/components/schema-matrix/SchemaMatrixView";
import { AIArchitectView } from "@/components/ai-terminal/AIArchitectView";

function App() {
  const activeTab = useNavigationStore((s) => s.activeTab);

  return (
    <AppShell>
      <div className="flex h-full">
        {activeTab === "catalog" && (
          <>
            <PipelineRegistry />
            <BentoWorkspace />
          </>
        )}
        {activeTab === "matrix" && <SchemaMatrixView />}
        {activeTab === "ai" && <AIArchitectView />}
      </div>
    </AppShell>
  );
}

export default App;
