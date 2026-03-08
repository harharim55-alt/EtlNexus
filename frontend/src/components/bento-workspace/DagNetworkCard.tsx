import { Network } from "lucide-react";
import { useDagNetworks } from "@/hooks/use-dag-networks";
import { Skeleton } from "@/components/ui/skeleton";

interface DagNetworkCardProps {
  pipelineId: string;
}

export function DagNetworkCard({ pipelineId }: DagNetworkCardProps) {
  const { data, isLoading } = useDagNetworks(pipelineId);

  return (
    <div className="col-span-12 bg-[#18181b] border border-white/5 rounded-2xl p-5">
      <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-4 flex items-center gap-2">
        <Network className="w-3.5 h-3.5" /> DAG Networks
      </h3>
      {isLoading ? (
        <div className="flex gap-2">
          <Skeleton className="h-8 w-32 bg-white/5 rounded-lg" />
          <Skeleton className="h-8 w-32 bg-white/5 rounded-lg" />
        </div>
      ) : data && data.networks.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {data.networks.map((net) => (
            <span
              key={net.network_name}
              className="text-xs font-mono px-3 py-1.5 rounded-lg bg-white/5 text-slate-300 border border-white/5"
            >
              {net.network_name}
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
