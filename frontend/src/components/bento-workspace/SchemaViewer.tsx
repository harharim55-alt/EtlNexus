import { Box } from "lucide-react";
import type { PipelineField } from "@/types/pipeline";

interface SchemaViewerProps {
  fields: PipelineField[];
}

function getDisplayDataType(field: PipelineField): string {
  if (field.data_type) return field.data_type;
  // Infer from field name as fallback
  const lower = field.name.toLowerCase();
  if (lower.includes("id")) return "UUID";
  if (lower.includes("amount") || lower.includes("price")) return "FLOAT8";
  if (lower.includes("date") || lower.includes("time") || lower.includes("created"))
    return "TIMESTAMP";
  if (lower.startsWith("is_") || lower.startsWith("has_")) return "BOOL";
  return "VARCHAR";
}

export function SchemaViewer({ fields }: SchemaViewerProps) {
  return (
    <div className="col-span-12 lg:col-span-7 bg-[#18181b] border border-white/5 rounded-2xl flex flex-col overflow-hidden max-h-[460px]">
      <div className="p-5 border-b border-white/5 bg-[#18181b]/50 backdrop-blur">
        <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
          <Box className="w-3.5 h-3.5" /> Data Structure
        </h3>
      </div>
      <div className="overflow-y-auto p-2 custom-scrollbar">
        {fields.map((field) => (
          <div
            key={field.id}
            className="flex justify-between items-center px-4 py-2.5 rounded-lg hover:bg-white/5 transition-colors group"
          >
            <div className="flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-slate-700 group-hover:bg-indigo-500 transition-colors" />
              <span className="font-mono text-sm text-slate-300 group-hover:text-white transition-colors">
                {field.name}
              </span>
            </div>
            <span className="text-[10px] text-slate-500 font-mono bg-[#09090b] px-2 py-1 rounded border border-white/5">
              {getDisplayDataType(field)}
            </span>
          </div>
        ))}
        {fields.length === 0 && (
          <div className="text-center text-slate-600 text-xs py-6 font-mono">
            No fields defined
          </div>
        )}
      </div>
    </div>
  );
}
