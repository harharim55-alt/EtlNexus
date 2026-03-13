import { useQuery } from "@tanstack/react-query";
import { fetchDagSummary } from "@/api/dag-summary";
import { useDateParams } from "@/stores/date-range-store";

export function useDagSummary() {
  const dateParams = useDateParams();
  return useQuery({
    queryKey: ["dag-summary", dateParams],
    queryFn: () => fetchDagSummary(dateParams),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });
}
