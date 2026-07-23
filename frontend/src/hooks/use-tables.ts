import { useQuery } from "@tanstack/react-query";
import { fetchTables } from "@/api/tables";

/** All catalog tables, optionally filtered server-side by team(s) + name. */
export function useTables(teams?: string[], q?: string) {
  return useQuery({
    queryKey: ["tables", teams ?? null, q ?? null],
    queryFn: () => fetchTables(teams, q),
    staleTime: 60_000,
  });
}
