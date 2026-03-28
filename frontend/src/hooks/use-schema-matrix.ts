import { useInfiniteQuery } from "@tanstack/react-query";
import { fetchSchemaMatrix } from "@/api/schema-matrix";

const PAGE_SIZE = 100;

export function useSchemaMatrix(searchQuery?: string) {
  const q = searchQuery?.trim() || undefined;
  return useInfiniteQuery({
    queryKey: ["schema-matrix", q ?? ""],
    queryFn: ({ pageParam = 0 }) => fetchSchemaMatrix(pageParam, PAGE_SIZE, q),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, p) => sum + p.fields.length, 0);
      return loaded < lastPage.total ? loaded : undefined;
    },
    staleTime: 5 * 60_000,
  });
}
