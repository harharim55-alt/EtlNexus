import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchPipelineLogs,
  createPipelineLog,
  updatePipelineLog,
  deletePipelineLog,
  setLogNetworks,
  setLogFields,
} from "@/api/pipeline-logs";

export function usePipelineLogs(pipelineId: string | null) {
  return useQuery({
    queryKey: ["pipeline-logs", pipelineId],
    queryFn: () => fetchPipelineLogs(pipelineId!),
    enabled: !!pipelineId,
    staleTime: 5 * 60_000,
  });
}

export function useCreatePipelineLog(pipelineId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: { name: string; ordinalPosition?: number }) =>
      createPipelineLog(pipelineId, params.name, params.ordinalPosition),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline-logs", pipelineId] });
    },
  });
}

export function useUpdatePipelineLog(pipelineId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ logId, body }: { logId: string; body: { name?: string; ordinal_position?: number } }) =>
      updatePipelineLog(pipelineId, logId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline-logs", pipelineId] });
    },
  });
}

export function useDeletePipelineLog(pipelineId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (logId: string) => deletePipelineLog(pipelineId, logId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline-logs", pipelineId] });
    },
  });
}

export function useSetLogNetworks(pipelineId: string, logId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (networks: { network_id: string; retention?: string }[]) =>
      setLogNetworks(pipelineId, logId, networks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline-logs", pipelineId] });
    },
  });
}

export function useSetLogFields(pipelineId: string, logId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fields: { name: string; data_type?: string; ordinal_position?: number }[]) =>
      setLogFields(pipelineId, logId, fields),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline-logs", pipelineId] });
    },
  });
}
