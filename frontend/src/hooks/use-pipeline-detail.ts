import { useQuery } from "@tanstack/react-query";
import { fetchPipelineDetail } from "@/api/pipelines";

export function usePipelineDetail(pipelineId: string | null) {
  return useQuery({
    queryKey: ["pipeline", pipelineId],
    queryFn: () => fetchPipelineDetail(pipelineId!),
    enabled: !!pipelineId,
    staleTime: 60_000,
  });
}
