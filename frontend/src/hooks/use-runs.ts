import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { fetchPipelineRuns, fetchRunDetail } from "@/api/resources";
import { useRunSelectorStore } from "@/stores/run-selector-store";

export function useRuns(pipelineId: string | null) {
  return useInfiniteQuery({
    queryKey: ["pipeline-runs", pipelineId],
    queryFn: ({ pageParam = 0 }) =>
      fetchPipelineRuns(pipelineId!, pageParam, 20),
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, p) => sum + p.items.length, 0);
      return loaded < lastPage.total ? loaded : undefined;
    },
    initialPageParam: 0,
    enabled: !!pipelineId,
    staleTime: 2 * 60_000,
  });
}

export function useRunDetail(pipelineId: string | null) {
  const dagRunId = useRunSelectorStore((s) => s.selectedDagRunId);
  return useQuery({
    queryKey: ["run-detail", pipelineId, dagRunId],
    queryFn: () => fetchRunDetail(pipelineId!, dagRunId!),
    enabled: !!pipelineId && !!dagRunId,
    staleTime: 5 * 60_000,
  });
}
