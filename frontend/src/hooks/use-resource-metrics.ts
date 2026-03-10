import { useQuery } from "@tanstack/react-query";
import { fetchResourceMetrics } from "@/api/resources";

export function useResourceMetrics(pipelineId: string | null) {
  return useQuery({
    queryKey: ["resource-metrics", pipelineId],
    queryFn: () => fetchResourceMetrics(pipelineId!),
    enabled: !!pipelineId,
    staleTime: 5 * 60_000,
  });
}
