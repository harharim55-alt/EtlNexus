import { useInfiniteQuery, keepPreviousData } from "@tanstack/react-query";
import { fetchPipelines } from "@/api/pipelines";

const PAGE_SIZE = 50;

export function usePipelines(searchQuery: string) {
  return useInfiniteQuery({
    queryKey: ["pipelines", searchQuery],
    queryFn: ({ pageParam = 0 }) =>
      fetchPipelines(searchQuery || undefined, pageParam, PAGE_SIZE),
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
