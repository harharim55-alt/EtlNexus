import { useQuery } from "@tanstack/react-query";
import { fetchPipelineConsumers } from "@/api/consumers";

export function usePipelineConsumers(etlName: string | null) {
  return useQuery({
    queryKey: ["pipeline-consumers", etlName],
    queryFn: () => fetchPipelineConsumers(etlName!),
    enabled: !!etlName,
    staleTime: 5 * 60_000,
  });
}
