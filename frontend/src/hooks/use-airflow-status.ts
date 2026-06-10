import { useQuery } from "@tanstack/react-query";
import { fetchAllAirflowStatuses } from "@/api/airflow";

export function useAirflowStatuses() {
  return useQuery({
    queryKey: ["airflow-statuses"],
    queryFn: fetchAllAirflowStatuses,
    refetchInterval: 5 * 60_000,
    staleTime: 5 * 60_000,
  });
}
