import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
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
  const scrollRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: fields.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 40,
    overscan: 10,
  });

  return (
    <div className="bg-card border border-border rounded-2xl flex flex-col overflow-hidden max-h-[460px]">
      <div className="p-5 border-b border-border bg-card/50 backdrop-blur">
        <h3 className="text-[11px] font-mono uppercase tracking-widest text-text-muted flex items-center gap-2">
          <Box className="w-3.5 h-3.5" /> Data Structure
        </h3>
      </div>
      <div ref={scrollRef} className="overflow-y-auto p-2 custom-scrollbar">
        {fields.length === 0 ? (
          <div className="text-center text-text-faint text-xs py-6 font-mono">
            No fields defined
          </div>
        ) : (
          <div
            style={{ height: `${virtualizer.getTotalSize()}px`, position: "relative" }}
          >
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const field = fields[virtualRow.index];
              return (
                <div
                  key={field.id}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                  className="flex justify-between items-center px-4 py-2.5 rounded-lg hover:bg-hover-bg transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-slate-700 group-hover:bg-indigo-500 transition-colors" />
                    <span className="font-mono text-sm text-text-primary group-hover:text-foreground transition-colors">
                      {field.name}
                    </span>
                  </div>
                  <span className="text-[10px] text-text-muted font-mono bg-background px-2 py-1 rounded border border-border">
                    {getDisplayDataType(field)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
