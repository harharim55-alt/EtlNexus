import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchTags, createTag, deleteTag, setPipelineTags } from "@/api/tags";

export function useTags(teamId?: string) {
  return useQuery({
    queryKey: ["tags", teamId],
    queryFn: () => fetchTags(teamId),
    staleTime: 5 * 60_000,
  });
}

export function useCreateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => createTag(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
  });
}

export function useDeleteTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tagId: string) => deleteTag(tagId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
  });
}

export function useSetPipelineTags(pipelineId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tagIds: string[]) => setPipelineTags(pipelineId, tagIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      queryClient.invalidateQueries({ queryKey: ["pipeline", pipelineId] });
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
    },
  });
}
