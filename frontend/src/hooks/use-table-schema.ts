import { useQuery } from "@tanstack/react-query";
import { fetchTableSchema } from "@/api/tables";

/** Lazily read a single table's schema live from Spark Connect. */
export function useTableSchema(namespace: string | null, table: string | null) {
  return useQuery({
    queryKey: ["table-schema", namespace, table],
    queryFn: () => fetchTableSchema(namespace!, table!),
    enabled: !!namespace && !!table,
    staleTime: 60_000,
  });
}
