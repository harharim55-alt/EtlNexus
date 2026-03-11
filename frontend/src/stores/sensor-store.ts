import { create } from "zustand";

interface SensorState {
  selectedSensors: string[];
  teamFilter: string | undefined;
  topologyMode: "union" | "intersection";
  toggleSensor: (sensorName: string) => void;
  clearSensors: () => void;
  setTeamFilter: (team: string | undefined) => void;
  setTopologyMode: (mode: "union" | "intersection") => void;
}

export const useSensorStore = create<SensorState>((set) => ({
  selectedSensors: [],
  teamFilter: undefined,
  topologyMode: "union",
  toggleSensor: (sensorName) =>
    set((state) => ({
      selectedSensors: state.selectedSensors.includes(sensorName)
        ? state.selectedSensors.filter((s) => s !== sensorName)
        : [...state.selectedSensors, sensorName],
    })),
  clearSensors: () => set({ selectedSensors: [] }),
  setTeamFilter: (team) => set({ teamFilter: team }),
  setTopologyMode: (mode) => set({ topologyMode: mode }),
}));
