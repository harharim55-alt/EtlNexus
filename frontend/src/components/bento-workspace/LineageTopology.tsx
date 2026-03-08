import { Database, Layers, Network } from "lucide-react";
import { useLineage } from "@/hooks/use-lineage";
import { Skeleton } from "@/components/ui/skeleton";

interface LineageTopologyProps {
  pipelineId: string;
  pipelineName: string;
  airflowStatus: string;
}

export function LineageTopology({
  pipelineId,
  pipelineName: _pipelineName,
  airflowStatus,
}: LineageTopologyProps) {
  const { data: lineage, isLoading } = useLineage(pipelineId);
  const isSuccess = airflowStatus === "success";

  if (isLoading) {
    return (
      <div className="col-span-12 lg:col-span-8 bg-[#18181b] border border-white/5 rounded-2xl p-6">
        <Skeleton className="h-6 w-40 mb-6 bg-white/5" />
        <Skeleton className="h-32 bg-white/5 rounded-xl" />
      </div>
    );
  }

  const sourceTables = lineage?.source_tables ?? [];
  const destinationTables = lineage?.destination_tables ?? [];

  return (
    <div className="col-span-12 lg:col-span-8 bg-[#18181b] border border-white/5 rounded-2xl p-6 relative overflow-hidden group">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      <h3 className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-6 flex items-center gap-2">
        <Network className="w-3.5 h-3.5" /> Pipeline Topology
      </h3>
      <div className="flex items-start justify-between w-full max-w-3xl mx-auto mt-4">
        {/* Source / Reads From */}
        <div className="flex flex-col items-center gap-3 w-40">
          <div className="w-12 h-12 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center shadow-lg">
            <Database className="w-5 h-5 text-slate-300" />
          </div>
          <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500 text-center">
            Reads From
          </span>
          <div className="flex flex-col gap-1.5 w-full mt-1">
            {sourceTables.map((t) => (
              <span
                key={t}
                title={t}
                className="text-[10px] bg-[#09090b] px-2 py-1.5 rounded text-slate-400 font-mono border border-white/5 truncate text-center"
              >
                {t}
              </span>
            ))}
            {sourceTables.length === 0 && (
              <span className="text-[10px] text-slate-600 font-mono text-center">
                No sources
              </span>
            )}
          </div>
        </div>

        {/* Flow line */}
        <div className="flex-1 px-4 relative flex items-center justify-center h-12">
          <div
            className={`h-[1px] w-full ${isSuccess ? "bg-emerald-500/30" : "bg-rose-500/30"} relative flex items-center justify-center`}
          >
            <div
              className={`absolute w-3 h-3 rounded-full ${
                isSuccess
                  ? "bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.8)]"
                  : "bg-rose-400 shadow-[0_0_10px_rgba(251,113,133,0.8)]"
              } z-10 animate-[pulse_2s_ease-in-out_infinite]`}
            />
          </div>
        </div>

        {/* Destination / Writes To */}
        <div className="flex flex-col items-center gap-3 w-40">
          <div className="w-12 h-12 bg-indigo-500/10 border border-indigo-500/30 rounded-xl flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.15)]">
            <Layers className="w-5 h-5 text-indigo-400" />
          </div>
          <span className="text-[10px] font-mono uppercase tracking-widest text-indigo-400/80 text-center">
            Writes To
          </span>
          <div className="flex flex-col gap-1.5 w-full mt-1">
            {destinationTables.map((t) => (
              <span
                key={t}
                title={t}
                className="text-[10px] bg-indigo-500/5 px-2 py-1.5 rounded text-indigo-300/80 font-mono border border-indigo-500/20 truncate text-center"
              >
                {t}
              </span>
            ))}
            {destinationTables.length === 0 && (
              <span className="text-[10px] text-slate-600 font-mono text-center">
                No destinations
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
