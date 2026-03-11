import { useQuery } from "@tanstack/react-query";
import { fetchUpstreamTopology } from "@/api/topology";

export function useUpstreamTopology(
  pipelineId: string | null,
  dagId?: string | null,
  enabled?: boolean,
) {
  return useQuery({
    queryKey: ["upstream-topology", pipelineId, dagId ?? null],
    queryFn: () => fetchUpstreamTopology(pipelineId!, dagId),
    enabled: !!pipelineId && enabled !== false,
    staleTime: 2 * 60_000,
  });
}
