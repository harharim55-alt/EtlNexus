import { useMutation, useQueryClient } from "@tanstack/react-query";
import { syncPipeline } from "@/api/pipelines";
import { toast } from "sonner";

export function useSyncPipeline(pipelineId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => syncPipeline(pipelineId),
    onSuccess: (data) => {
      toast.success(`Synced "${data.pipeline_name}" from Airflow`);
      queryClient.invalidateQueries({ queryKey: ["pipeline", pipelineId] });
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      queryClient.invalidateQueries({ queryKey: ["airflow-statuses"] });
      queryClient.invalidateQueries({ queryKey: ["resource-metrics", pipelineId] });
      queryClient.invalidateQueries({ queryKey: ["lineage", pipelineId] });
      queryClient.invalidateQueries({ queryKey: ["topology", pipelineId] });
      queryClient.invalidateQueries({ queryKey: ["execution-plan", pipelineId] });
      queryClient.invalidateQueries({ queryKey: ["execution-plan-runs", pipelineId] });
      queryClient.invalidateQueries({ queryKey: ["pipeline-runs", pipelineId] });
      queryClient.invalidateQueries({ queryKey: ["resource-history", pipelineId] });
    },
    onError: () => {
      toast.error("Failed to sync pipeline from Airflow");
    },
  });
}
