import type { FieldFrequencyRow as FieldFrequencyRowType } from "@/types/schema-matrix";
import { stripDummy } from "@/lib/format";

interface FieldFrequencyRowProps {
  row: FieldFrequencyRowType;
}

export function FieldFrequencyRow({ row }: FieldFrequencyRowProps) {
  return (
    <div className="flex items-center gap-4 px-5 py-3 rounded-xl hover:bg-hover-bg transition-colors group">
      {/* Field Name */}
      <div className="w-48 shrink-0">
        <span className="font-mono text-sm text-text-primary group-hover:text-foreground transition-colors">
          {row.field_name}
        </span>
      </div>

      {/* Frequency Bar */}
      <div className="w-24 shrink-0 flex items-center gap-2">
        <div className="flex-1 h-1.5 bg-hover-bg rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all"
            style={{ width: `${Math.min(row.frequency * 20, 100)}%` }}
          />
        </div>
        <span className="text-[10px] font-mono text-text-muted w-4 text-right">
          {row.frequency}
        </span>
      </div>

      {/* Pipeline Tags */}
      <div className="flex-1 flex flex-wrap gap-1.5">
        {row.pipelines.map((p) => (
          <span
            key={p.pipeline_id}
            className="text-[10px] font-mono px-2 py-1 rounded bg-hover-bg text-text-secondary border border-border hover:text-text-primary hover:border-border-prominent transition-colors"
          >
            {stripDummy(p.pipeline_name)}
          </span>
        ))}
      </div>
    </div>
  );
}
