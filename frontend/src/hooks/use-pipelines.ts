import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { fetchPipelines } from "@/api/pipelines";

export function usePipelines(searchQuery: string) {
  return useQuery({
    queryKey: ["pipelines", searchQuery],
    queryFn: () => fetchPipelines(searchQuery || undefined),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
    placeholderData: keepPreviousData,
  });
}
