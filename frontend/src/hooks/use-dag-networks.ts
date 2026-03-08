import { useQuery } from "@tanstack/react-query";
import { fetchDagNetworks } from "@/api/dag-networks";

export function useDagNetworks(pipelineId: string | null) {
  return useQuery({
    queryKey: ["dag-networks", pipelineId],
    queryFn: () => fetchDagNetworks(pipelineId!),
    enabled: !!pipelineId,
    staleTime: 5 * 60_000,
  });
}
