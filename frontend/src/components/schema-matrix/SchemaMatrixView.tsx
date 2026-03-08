import { Network } from "lucide-react";
import { useSchemaMatrix } from "@/hooks/use-schema-matrix";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { FieldFrequencyRow } from "./FieldFrequencyRow";

export function SchemaMatrixView() {
  const { data, isLoading, error, refetch } = useSchemaMatrix();

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <LoadingState />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <ErrorState message="Failed to load schema matrix" onRetry={refetch} />
      </div>
    );
  }

  if (!data || data.fields.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <EmptyState message="No shared fields found across pipelines" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar">
      <div className="p-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-indigo-500/10 p-2 rounded-lg border border-indigo-500/20">
              <Network className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-white">Field Frequency Matrix</h1>
              <p className="text-xs text-slate-500 font-mono mt-0.5">
                Fields shared across 2+ pipelines — {data.fields.length} fields found
              </p>
            </div>
          </div>
        </div>

        {/* Column Headers */}
        <div className="flex items-center gap-4 px-5 py-2 text-[10px] font-mono uppercase tracking-widest text-slate-600 border-b border-white/5 mb-2">
          <div className="w-48 shrink-0">Field Name</div>
          <div className="w-24 shrink-0">Frequency</div>
          <div className="flex-1">Pipelines</div>
        </div>

        {/* Rows */}
        <div className="space-y-0.5">
          {data.fields.map((row) => (
            <FieldFrequencyRow key={row.field_name} row={row} />
          ))}
        </div>
      </div>
    </div>
  );
}
