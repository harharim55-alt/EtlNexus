import { useQuery } from "@tanstack/react-query";
import { fetchSensors, fetchSensorTopology } from "@/api/sensors";

export function useSensors(team?: string) {
  return useQuery({
    queryKey: ["sensors", team ?? "all"],
    queryFn: () => fetchSensors(team),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });
}

export function useSensorTopology(sensorNames: string[], mode: string = "union") {
  return useQuery({
    queryKey: ["sensor-topology", ...sensorNames.sort(), mode],
    queryFn: () => fetchSensorTopology(sensorNames, mode),
    enabled: sensorNames.length > 0,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
