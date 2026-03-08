import type { FieldFrequencyRow as FieldFrequencyRowType } from "@/types/schema-matrix";

interface FieldFrequencyRowProps {
  row: FieldFrequencyRowType;
}

export function FieldFrequencyRow({ row }: FieldFrequencyRowProps) {
  return (
    <div className="flex items-center gap-4 px-5 py-3 rounded-xl hover:bg-white/5 transition-colors group">
      {/* Field Name */}
      <div className="w-48 shrink-0">
        <span className="font-mono text-sm text-slate-200 group-hover:text-white transition-colors">
          {row.field_name}
        </span>
      </div>

      {/* Frequency Bar */}
      <div className="w-24 shrink-0 flex items-center gap-2">
        <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all"
            style={{ width: `${Math.min(row.frequency * 20, 100)}%` }}
          />
        </div>
        <span className="text-[10px] font-mono text-slate-500 w-4 text-right">
          {row.frequency}
        </span>
      </div>

      {/* Pipeline Tags */}
      <div className="flex-1 flex flex-wrap gap-1.5">
        {row.pipelines.map((p) => (
          <span
            key={p.pipeline_id}
            className="text-[10px] font-mono px-2 py-1 rounded bg-white/5 text-slate-400 border border-white/5 hover:text-slate-200 hover:border-white/10 transition-colors"
          >
            {p.pipeline_name}
          </span>
        ))}
      </div>
    </div>
  );
}
