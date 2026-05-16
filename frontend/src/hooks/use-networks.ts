import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchNetworks, createNetwork } from "@/api/networks";

export function useNetworks() {
  return useQuery({
    queryKey: ["networks"],
    queryFn: fetchNetworks,
    staleTime: 10 * 60_000,
  });
}

export function useCreateNetwork() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, description }: { name: string; description?: string }) =>
      createNetwork(name, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["networks"] });
    },
  });
}
