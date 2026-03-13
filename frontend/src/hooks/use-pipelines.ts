import { useInfiniteQuery, keepPreviousData } from "@tanstack/react-query";
import { fetchPipelines } from "@/api/pipelines";
import { useDateParams } from "@/stores/date-range-store";

const PAGE_SIZE = 50;

export function usePipelines(searchQuery: string) {
  const dateParams = useDateParams();
  return useInfiniteQuery({
    queryKey: ["pipelines", searchQuery, dateParams],
    queryFn: ({ pageParam = 0 }) =>
      fetchPipelines(searchQuery || undefined, pageParam, PAGE_SIZE, dateParams),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, p) => sum + p.items.length, 0);
      return loaded < lastPage.total ? loaded : undefined;
    },
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
    placeholderData: keepPreviousData,
  });
}
