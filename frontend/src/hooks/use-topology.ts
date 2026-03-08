import { useQuery } from "@tanstack/react-query";
import { fetchTopology } from "@/api/topology";

export function useTopology(
  pipelineId: string | null,
  dagId?: string | null,
) {
  return useQuery({
    queryKey: ["topology", pipelineId, dagId ?? null],
    queryFn: () => fetchTopology(pipelineId!, dagId),
    enabled: !!pipelineId,
    staleTime: 2 * 60_000,
  });
}
