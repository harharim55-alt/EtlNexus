import { useQuery } from "@tanstack/react-query";
import { fetchJoinSuggestions } from "@/api/pipelines";

export function useJoinSuggestions(pipelineId: string | null) {
  return useQuery({
    queryKey: ["join-suggestions", pipelineId],
    queryFn: () => fetchJoinSuggestions(pipelineId!),
    enabled: !!pipelineId,
    staleTime: 5 * 60_000,
  });
}
