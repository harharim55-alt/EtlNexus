import { useEffect, useState } from "react";
import { Layers, Pencil, Table2, X } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import apiClient from "@/api/client";
import { usePipelineDetail } from "@/hooks/use-pipeline-detail";
import { useUpdatePipeline } from "@/hooks/use-update-pipeline";
import { useDataProductStore } from "@/stores/data-product-store";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { BentoHeader } from "@/components/bento-workspace/BentoHeader";
import { DocumentationPreview } from "@/components/bento-workspace/DocumentationPreview";
import { ConsumeSnippet } from "@/components/bento-workspace/ConsumeSnippet";
import { SchemaViewer } from "@/components/bento-workspace/SchemaViewer";
import { columnsToFields, type TableSchema } from "@/types/table";
import type { PipelineDetail } from "@/types/pipeline";
import { stripDummy } from "@/lib/format";
import { TableSelect, type TableRef } from "./TableSelect";

const tableKey = (t: TableSchema | TableRef) => `${t.namespace}.${t.table_name}`;

export function DataProductWorkspace() {
  const selectedProductId = useDataProductStore((s) => s.selectedProductId);
  const { data: pipeline, isLoading, error, refetch } = usePipelineDetail(selectedProductId);
  const { mutate: updatePipeline, isPending: isSaving } = useUpdatePipeline(selectedProductId ?? "");
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);

  const tables = pipeline?.tables ?? [];

  useEffect(() => {
    if (tables.length === 0) {
      setActiveKey(null);
    } else if (!activeKey || !tables.some((t) => tableKey(t) === activeKey)) {
      setActiveKey(tableKey(tables[0]));
    }
  }, [tables, activeKey]);

  if (!selectedProductId) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-faint">
        <p className="text-sm font-mono">Select a data product to explore</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
        <Skeleton className="h-8 w-64 bg-hover-bg mb-2" />
        <Skeleton className="h-5 w-96 bg-hover-bg mb-8" />
        <div className="grid grid-cols-12 gap-6">
          <Skeleton className="col-span-12 h-24 bg-hover-bg rounded-2xl" />
          <Skeleton className="col-span-12 h-64 bg-hover-bg rounded-2xl" />
        </div>
      </div>
    );
  }

  if (error || !pipeline) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <ErrorState message="Failed to load data product" onRetry={refetch} />
      </div>
    );
  }

  const activeTable = tables.find((t) => tableKey(t) === activeKey) ?? null;

  return (
    <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
      <BentoHeader
        pipeline={pipeline}
        onSaveDescription={(description) => updatePipeline({ description })}
        isSaving={isSaving}
        canEdit={pipeline.can_edit}
      />

      <div className="grid grid-cols-12 gap-6 mt-6">
        {/* Documentation */}
        <DocumentationPreview
          pipelineId={pipeline.id}
          pipelineName={stripDummy(pipeline.name)}
          documentation={pipeline.documentation}
          onSave={(doc) => updatePipeline({ documentation: doc })}
          isSaving={isSaving}
          canEdit={pipeline.can_edit}
        />

        {/* Product-level consume snippet (read_by_tag, read-only) */}
        <div className="col-span-12">
          <ConsumeSnippet snippet={pipeline.import_snippet || pipeline.default_import_snippet} />
        </div>
      </div>

      {/* Tables that make up the product */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-[11px] font-mono uppercase tracking-widest text-text-muted flex items-center gap-2">
            <Layers className="w-3.5 h-3.5" /> Tables
          </h2>
          {pipeline.can_edit && (
            <button
              onClick={() => setEditOpen(true)}
              className="flex items-center gap-1.5 text-[11px] font-mono text-text-muted hover:text-indigo-400 border border-border hover:border-indigo-500/40 px-2.5 py-1 rounded-lg transition-colors cursor-pointer"
            >
              <Pencil className="size-3" /> Edit tables
            </button>
          )}
        </div>

        {tables.length === 0 ? (
          <p className="text-sm text-text-faint font-mono">
            No tables yet.{pipeline.can_edit ? " Use “Edit tables” to add some." : ""}
          </p>
        ) : (
          <>
            <div className="flex items-center gap-1 flex-wrap border-b border-border mb-6">
              {tables.map((t) => (
                <button
                  key={tableKey(t)}
                  type="button"
                  onClick={() => setActiveKey(tableKey(t))}
                  className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium -mb-px border-b-2 transition-colors cursor-pointer ${
                    activeKey === tableKey(t)
                      ? "border-indigo-500 text-indigo-400"
                      : "border-transparent text-text-muted hover:text-text-primary"
                  }`}
                >
                  <Table2 className="size-3.5" />
                  <span className="font-mono">{t.table_name}</span>
                </button>
              ))}
            </div>

            {activeTable && (
              <div className="grid grid-cols-12 gap-6">
                <div className="col-span-12 lg:col-span-7">
                  <SchemaViewer fields={columnsToFields(activeTable)} canEdit={false} />
                </div>
                <div className="col-span-12 lg:col-span-5">
                  <ConsumeSnippet snippet={activeTable.consume_snippet} />
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {editOpen && (
        <EditTablesModal pipeline={pipeline} onClose={() => setEditOpen(false)} />
      )}
    </div>
  );
}

/* ── Edit-tables modal ──────────────────────────────────────────────── */

function EditTablesModal({ pipeline, onClose }: { pipeline: PipelineDetail; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [tables, setTables] = useState<TableRef[]>(
    pipeline.tables.map((t) => ({ namespace: t.namespace, table_name: t.table_name }))
  );

  const mutation = useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.put<PipelineDetail>(
        `/data-products/${pipeline.id}/tables`,
        { tables }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline", pipeline.id] });
      queryClient.invalidateQueries({ queryKey: ["data-products"] });
      toast.success("Tables updated");
      onClose();
    },
    onError: (err) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail || "Failed to update tables");
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-in fade-in duration-150">
      <div className="bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl animate-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between p-5 border-b border-border">
          <h2 className="text-lg font-semibold text-foreground">Edit Tables</h2>
          <button onClick={onClose} className="p-1 text-text-muted hover:text-foreground cursor-pointer">
            <X className="size-4" />
          </button>
        </div>
        <div className="p-5">
          <TableSelect team={pipeline.team} value={tables} onChange={setTables} />
        </div>
        <div className="flex justify-end gap-2 p-5 border-t border-border">
          <button onClick={onClose} className="px-4 py-2 text-sm text-text-secondary hover:text-foreground rounded-lg">
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {mutation.isPending ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
