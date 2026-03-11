import { AxiosError } from "axios";
import apiClient from "./client";
import type { ExecutionPlanResponse } from "@/types/execution-plan";

export async function fetchExecutionPlan(
  pipelineId: string,
): Promise<ExecutionPlanResponse | null> {
  try {
    const { data } = await apiClient.get<ExecutionPlanResponse>(
      `/pipelines/${pipelineId}/execution-plan`,
    );
    return data;
  } catch (err) {
    if (err instanceof AxiosError && err.response?.status === 404) {
      return null;
    }
    throw err;
  }
}
