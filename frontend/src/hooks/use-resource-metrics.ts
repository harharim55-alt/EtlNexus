import { useQuery } from "@tanstack/react-query";
import { fetchResourceMetrics } from "@/api/resources";
import { useDateParams } from "@/stores/date-range-store";

export function useResourceMetrics(pipelineId: string | null) {
  const dateParams = useDateParams();
  return useQuery({
    queryKey: ["resource-metrics", pipelineId, dateParams],
    queryFn: () => fetchResourceMetrics(pipelineId!, dateParams),
    enabled: !!pipelineId,
    staleTime: 5 * 60_000,
  });
}
