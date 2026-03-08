import { useQuery } from "@tanstack/react-query";
import { fetchPipelineUsage } from "@/api/usage";

export function usePipelineUsage(etlName: string | null) {
  return useQuery({
    queryKey: ["pipeline-usage", etlName],
    queryFn: () => fetchPipelineUsage(etlName!),
    enabled: !!etlName,
    staleTime: 5 * 60_000,
  });
}
