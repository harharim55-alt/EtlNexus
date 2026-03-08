import { useQuery } from "@tanstack/react-query";
import { fetchSchemaMatrix } from "@/api/schema-matrix";

export function useSchemaMatrix() {
  return useQuery({
    queryKey: ["schema-matrix"],
    queryFn: fetchSchemaMatrix,
    staleTime: 5 * 60_000,
  });
}
