import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchRevisions, restoreRevision } from "@/api/pipelines";
import { toast } from "sonner";

export function useRevisions(
  pipelineId: string,
  field?: "description" | "documentation",
  enabled = true,
) {
  return useQuery({
    queryKey: ["revisions", pipelineId, field],
    queryFn: () => fetchRevisions(pipelineId, field),
    enabled: enabled && !!pipelineId,
  });
}

export function useRestoreRevision(pipelineId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (revisionId: string) => restoreRevision(pipelineId, revisionId),
    onSuccess: () => {
      toast.success("Revision restored");
      queryClient.invalidateQueries({ queryKey: ["pipeline", pipelineId] });
      queryClient.invalidateQueries({ queryKey: ["revisions", pipelineId] });
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
    },
    onError: () => {
      toast.error("Failed to restore revision");
    },
  });
}
