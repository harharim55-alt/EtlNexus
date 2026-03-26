import { useQuery } from "@tanstack/react-query";
import { fetchUpstreamTopology } from "@/api/topology";

export function useUpstreamTopology(
  pipelineId: string | null,
  dagId?: string | null,
  enabled?: boolean,
  dagRunId?: string | null,
) {
  return useQuery({
    queryKey: ["upstream-topology", pipelineId, dagId ?? null, dagRunId ?? null],
    queryFn: () => fetchUpstreamTopology(pipelineId!, dagId, dagRunId),
    enabled: !!pipelineId && enabled !== false,
    staleTime: 2 * 60_000,
  });
}
