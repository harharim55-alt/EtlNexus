import { useQuery } from "@tanstack/react-query";
import { fetchResourceHistory } from "@/api/resources";
import { useDateParams } from "@/stores/date-range-store";

export function useResourceHistory(pipelineId: string | null) {
  const dateParams = useDateParams();
  return useQuery({
    queryKey: ["resource-history", pipelineId, dateParams],
    queryFn: () => fetchResourceHistory(pipelineId!, dateParams),
    enabled: !!pipelineId,
    staleTime: 5 * 60_000,
  });
}
