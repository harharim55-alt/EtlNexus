import { useQuery } from "@tanstack/react-query";
import { fetchLineage } from "@/api/lineage";

export function useLineage(pipelineId: string | null) {
  return useQuery({
    queryKey: ["lineage", pipelineId],
    queryFn: () => fetchLineage(pipelineId!),
    enabled: !!pipelineId,
    staleTime: 5 * 60_000,
  });
}
