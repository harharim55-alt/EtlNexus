import { Radio } from "lucide-react";
import { useSensors } from "@/hooks/use-sensors";
import { useSensorStore } from "@/stores/sensor-store";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { TeamFilter } from "./TeamFilter";
import { SensorCard } from "./SensorCard";
import { SensorTopology } from "./SensorTopology";

export function SensorsView() {
  const teamFilter = useSensorStore((s) => s.teamFilter);
  const selectedSensors = useSensorStore((s) => s.selectedSensors);
  const clearSensors = useSensorStore((s) => s.clearSensors);
  const { data, isLoading, error, refetch } = useSensors(teamFilter);

  if (isLoading) {
    return (
      <div data-section="sensors-view" className="flex-1 flex items-center justify-center">
        <LoadingState />
      </div>
    );
  }

  if (error) {
    return (
      <div data-section="sensors-view" className="flex-1 flex items-center justify-center">
        <ErrorState message="Failed to load sensors" onRetry={refetch} />
      </div>
    );
  }

  if (!data || data.sensors.length === 0) {
    return (
      <div data-section="sensors-view" className="flex-1 flex items-center justify-center">
        <EmptyState message="No sensors found" />
      </div>
    );
  }

  return (
    <div data-section="sensors-view" className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="shrink-0 px-8 pt-8 pb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="bg-teal-500/10 p-2 rounded-lg border border-teal-500/20">
              <Radio className="w-5 h-5 text-teal-400" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-white">
                Sensor Dashboard
              </h1>
              <p className="text-xs text-slate-500 font-mono mt-0.5">
                {data.sensors.length} sensors across {data.teams.length} teams
              </p>
            </div>
          </div>

          {selectedSensors.length > 0 && (
            <button
              type="button"
              onClick={clearSensors}
              className="text-[10px] font-mono px-3 py-1.5 rounded-lg border border-white/10 text-slate-400 hover:text-white hover:border-white/20 transition-all cursor-pointer"
            >
              Clear selection ({selectedSensors.length})
            </button>
          )}
        </div>

        {/* Team filter */}
        <TeamFilter teams={data.teams} />
      </div>

      {/* Main content: Split layout */}
      <div className="flex-1 flex min-h-0">
        {/* Left: Sensor grid */}
        <div className="w-[45%] border-r border-white/5 overflow-y-auto custom-scrollbar p-4">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
            {data.sensors.map((sensor) => (
              <SensorCard key={sensor.id} sensor={sensor} />
            ))}
          </div>
        </div>

        {/* Right: Topology */}
        <div className="w-[55%] flex flex-col min-h-0">
          <SensorTopology />
        </div>
      </div>
    </div>
  );
}
