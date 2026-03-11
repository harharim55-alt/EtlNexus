import { useQuery } from "@tanstack/react-query";
import { fetchExecutionPlan } from "@/api/execution-plan";

export function useExecutionPlan(pipelineId: string | null) {
  return useQuery({
    queryKey: ["execution-plan", pipelineId],
    queryFn: () => fetchExecutionPlan(pipelineId!),
    enabled: !!pipelineId,
    staleTime: 5 * 60_000,
    retry: false,
  });
}
