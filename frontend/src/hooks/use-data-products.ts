import { useInfiniteQuery } from "@tanstack/react-query";
import { fetchPipelines, type PipelineFilterParams } from "@/api/pipelines";

export function useDataProducts(
  searchQuery: string,
  filters?: PipelineFilterParams,
) {
  return useInfiniteQuery({
    queryKey: ["data-products", searchQuery, filters],
    queryFn: ({ pageParam = 0 }) =>
      fetchPipelines(
        searchQuery || undefined,
        pageParam,
        50,
        undefined,
        { ...filters, is_data_product: true },
      ),
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, p) => sum + p.items.length, 0);
      return loaded < lastPage.total ? loaded : undefined;
    },
    initialPageParam: 0,
    staleTime: 2 * 60_000,
  });
}
