import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchTags, fetchTagMembers, setPipelineTags } from "@/api/tags";

/** All tag-products, for the tag picker. */
export function useTags() {
  return useQuery({
    queryKey: ["tags"],
    queryFn: () => fetchTags(),
    staleTime: 5 * 60_000,
  });
}

/** Products tagged with a given tag — drives the tag detail page's tabs. */
export function useTagMembers(tagId: string | null) {
  return useQuery({
    queryKey: ["tag-members", tagId],
    queryFn: () => fetchTagMembers(tagId!),
    enabled: !!tagId,
    staleTime: 60_000,
  });
}

export function useSetPipelineTags(pipelineId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tagIds: string[]) => setPipelineTags(pipelineId, tagIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      queryClient.invalidateQueries({ queryKey: ["tag-members"] });
      queryClient.invalidateQueries({ queryKey: ["pipeline", pipelineId] });
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
    },
  });
}
