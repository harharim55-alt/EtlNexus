import { useQuery, useInfiniteQuery, keepPreviousData } from "@tanstack/react-query";
import { fetchExecutionPlan, fetchExecutionPlanRuns } from "@/api/execution-plan";

const RUNS_PAGE_SIZE = 20;

export function useExecutionPlan(pipelineId: string | null, dagRunId?: string) {
  return useQuery({
    queryKey: ["execution-plan", pipelineId, dagRunId],
    queryFn: () => fetchExecutionPlan(pipelineId!, dagRunId),
    enabled: !!pipelineId,
    staleTime: 5 * 60_000,
    retry: false,
  });
}

export function useExecutionPlanRuns(pipelineId: string | null) {
  return useInfiniteQuery({
    queryKey: ["execution-plan-runs", pipelineId],
    queryFn: ({ pageParam = 0 }) =>
      fetchExecutionPlanRuns(pipelineId!, pageParam, RUNS_PAGE_SIZE),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, p) => sum + p.items.length, 0);
      return loaded < lastPage.total ? loaded : undefined;
    },
    enabled: !!pipelineId,
    staleTime: 5 * 60_000,
    placeholderData: keepPreviousData,
  });
}
