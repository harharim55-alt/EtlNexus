import { useQuery } from "@tanstack/react-query";
import { fetchPipelineUsage } from "@/api/usage";

export function usePipelineUsage(pipelineId: string | null) {
  return useQuery({
    queryKey: ["pipeline-usage", pipelineId],
    queryFn: () => fetchPipelineUsage(pipelineId!),
    enabled: !!pipelineId,
    staleTime: 5 * 60_000,
  });
}
