import { useMutation, useQueryClient } from "@tanstack/react-query";
import { promoteToDataProduct } from "@/api/pipelines";
import { toast } from "sonner";

export function usePromoteToDataProduct() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (pipelineId: string) => promoteToDataProduct(pipelineId),
    onSuccess: () => {
      toast.success("Pipeline promoted to data product");
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
    },
    onError: () => {
      toast.error("Failed to promote pipeline");
    },
  });
}
