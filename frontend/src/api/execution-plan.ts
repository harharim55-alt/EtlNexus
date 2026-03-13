import { AxiosError } from "axios";
import apiClient from "./client";
import type { ExecutionPlanResponse, ExecutionPlanRunsResponse } from "@/types/execution-plan";

export async function fetchExecutionPlan(
  pipelineId: string,
  dagRunId?: string,
): Promise<ExecutionPlanResponse | null> {
  try {
    const params = dagRunId ? { dag_run_id: dagRunId } : {};
    const { data } = await apiClient.get<ExecutionPlanResponse>(
      `/pipelines/${pipelineId}/execution-plan`,
      { params },
    );
    return data;
  } catch (err) {
    if (err instanceof AxiosError && err.response?.status === 404) {
      return null;
    }
    throw err;
  }
}

export async function fetchExecutionPlanRuns(
  pipelineId: string,
  skip: number,
  limit: number,
): Promise<ExecutionPlanRunsResponse> {
  const { data } = await apiClient.get<ExecutionPlanRunsResponse>(
    `/pipelines/${pipelineId}/execution-plan/runs`,
    { params: { skip, limit } },
  );
  return data;
}
