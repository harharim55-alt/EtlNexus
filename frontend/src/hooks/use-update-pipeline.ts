import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updatePipeline } from "@/api/pipelines";
import type { PipelineUpdateRequest } from "@/types/pipeline";
import { toast } from "sonner";

export function useUpdatePipeline(pipelineId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: PipelineUpdateRequest) => updatePipeline(pipelineId, body),
    onSuccess: () => {
      toast.success("Pipeline updated");
      queryClient.invalidateQueries({ queryKey: ["pipeline", pipelineId] });
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
    },
    onError: () => {
      toast.error("Failed to update pipeline");
    },
  });
}
