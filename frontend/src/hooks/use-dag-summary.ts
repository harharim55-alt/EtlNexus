import { useQuery } from "@tanstack/react-query";
import { fetchDagSummary } from "@/api/dag-summary";

export function useDagSummary() {
  return useQuery({
    queryKey: ["dag-summary"],
    queryFn: fetchDagSummary,
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });
}
