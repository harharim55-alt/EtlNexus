import { useQuery } from "@tanstack/react-query";
import { fetchPipelineConsumers } from "@/api/consumers";

export function usePipelineConsumers(pipelineId: string | null) {
  return useQuery({
    queryKey: ["pipeline-consumers", pipelineId],
    queryFn: () => fetchPipelineConsumers(pipelineId!),
    enabled: !!pipelineId,
    staleTime: 5 * 60_000,
  });
}
