import { Network } from "lucide-react";
import { useTopology } from "@/hooks/use-topology";
import { Skeleton } from "@/components/ui/skeleton";

interface DagNetworkCardProps {
  pipelineId: string;
}

export function DagNetworkCard({ pipelineId }: DagNetworkCardProps) {
  const { data: topology, isLoading } = useTopology(pipelineId);
  const dagIds = topology?.dag_ids ?? [];

  return (
    <div className="col-span-12 lg:col-span-5 bg-[#18181b] border border-white/5 rounded-2xl p-5">
      <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-4 flex items-center gap-2">
        <Network className="w-3.5 h-3.5" /> DAG Networks
      </h3>
      {isLoading ? (
        <div className="flex gap-2">
          <Skeleton className="h-8 w-32 bg-white/5 rounded-lg" />
          <Skeleton className="h-8 w-32 bg-white/5 rounded-lg" />
        </div>
      ) : dagIds.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {dagIds.map((dagId) => (
            <span
              key={dagId}
              className="text-xs font-mono px-3 py-1.5 rounded-lg bg-white/5 text-slate-300 border border-white/5"
            >
              {dagId}
            </span>
          ))}
        </div>
      ) : (
        <div className="text-xs text-slate-600 font-mono">
          No DAG networks configured
        </div>
      )}
    </div>
  );
}
