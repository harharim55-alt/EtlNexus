import { useQuery } from "@tanstack/react-query";
import { fetchAllAirflowStatuses } from "@/api/airflow";

export function useAirflowStatuses() {
  return useQuery({
    queryKey: ["airflow-statuses"],
    queryFn: fetchAllAirflowStatuses,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}
