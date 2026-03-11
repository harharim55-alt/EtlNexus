import apiClient from "./client";
import type { SensorListResponse, SensorTopologyResponse } from "@/types/sensor";

export async function fetchSensors(team?: string): Promise<SensorListResponse> {
  const params = team ? { team } : {};
  const { data } = await apiClient.get<SensorListResponse>("/sensors", { params });
  return data;
}

export async function fetchSensorTopology(
  sensorNames: string[],
  mode: string = "union",
): Promise<SensorTopologyResponse> {
  const params = new URLSearchParams();
  for (const name of sensorNames) {
    params.append("sensors", name);
  }
  params.append("mode", mode);
  const { data } = await apiClient.get<SensorTopologyResponse>(
    `/sensors/topology?${params.toString()}`,
  );
  return data;
}
