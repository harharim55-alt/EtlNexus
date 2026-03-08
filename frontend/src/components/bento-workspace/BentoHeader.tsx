import { StatusBadge } from "@/components/shared/StatusBadge";
import type { PipelineDetail } from "@/types/pipeline";

interface BentoHeaderProps {
  pipeline: PipelineDetail;
}

export function BentoHeader({ pipeline }: BentoHeaderProps) {
  return (
    <div className="flex justify-between items-start mb-4">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <span className="text-[10px] font-mono uppercase tracking-widest text-indigo-400 bg-indigo-500/10 px-2 py-1 rounded border border-indigo-500/20">
            {pipeline.category}
          </span>
          <StatusBadge status={pipeline.airflow_status} size="md" />
        </div>
        <h1 className="text-3xl font-semibold text-white tracking-tight">
          {pipeline.name}
        </h1>
        <p className="text-slate-400 mt-2 max-w-2xl text-sm leading-relaxed">
          {pipeline.description}
        </p>
      </div>
    </div>
  );
}
