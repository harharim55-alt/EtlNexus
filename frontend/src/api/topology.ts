import apiClient from "./client";
import type { TopologyGraph } from "@/types/topology";

export async function fetchTopology(
  pipelineId: string,
  dagId?: string | null,
): Promise<TopologyGraph> {
  const params = dagId ? { dag_id: dagId } : {};
  const { data } = await apiClient.get<TopologyGraph>(
    `/pipelines/${pipelineId}/topology`,
    { params },
  );
  return data;
}
