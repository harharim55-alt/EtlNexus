import { useQuery } from "@tanstack/react-query";
import { fetchTables } from "@/api/tables";

/** All catalog tables, optionally filtered server-side by team + name. */
export function useTables(team?: string, q?: string) {
  return useQuery({
    queryKey: ["tables", team ?? null, q ?? null],
    queryFn: () => fetchTables(team, q),
    staleTime: 60_000,
  });
}
