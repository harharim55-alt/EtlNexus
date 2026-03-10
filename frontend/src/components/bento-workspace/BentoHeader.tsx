import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useSyncPipeline } from "@/hooks/use-sync-pipeline";
import type { PipelineDetail } from "@/types/pipeline";

interface BentoHeaderProps {
  pipeline: PipelineDetail;
}

export function BentoHeader({ pipeline }: BentoHeaderProps) {
  const { mutate: sync, isPending } = useSyncPipeline(pipeline.id);

  return (
    <div className="flex justify-between items-start mb-4">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <StatusBadge status={pipeline.airflow_status} size="md" />
        </div>
        <h1 className="text-3xl font-semibold text-white tracking-tight">
          {pipeline.name}
        </h1>
        <p className="text-slate-400 mt-2 max-w-2xl text-sm leading-relaxed">
          {pipeline.description}
        </p>
      </div>

      <Tooltip>
        <TooltipTrigger
          render={
            <Button
              variant="outline"
              size="sm"
              disabled={isPending}
              onClick={() => sync()}
              className="border-white/10 bg-white/[0.03] text-slate-400 hover:text-white hover:bg-white/[0.07] transition-all duration-200"
            />
          }
        >
          <RefreshCw
            className={`size-3.5 ${isPending ? "animate-spin" : ""}`}
          />
          <span className="text-xs">
            {isPending ? "Syncing\u2026" : "Sync"}
          </span>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          Refresh this pipeline from Airflow
        </TooltipContent>
      </Tooltip>
    </div>
  );
}
