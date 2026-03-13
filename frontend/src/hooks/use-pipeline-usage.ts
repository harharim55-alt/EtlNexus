import { useQuery } from "@tanstack/react-query";
import { fetchPipelineUsage } from "@/api/usage";
import { useDateParams } from "@/stores/date-range-store";

export function usePipelineUsage(etlName: string | null) {
  const dateParams = useDateParams();
  return useQuery({
    queryKey: ["pipeline-usage", etlName, dateParams],
    queryFn: () => fetchPipelineUsage(etlName!, dateParams),
    enabled: !!etlName,
    staleTime: 5 * 60_000,
  });
}
