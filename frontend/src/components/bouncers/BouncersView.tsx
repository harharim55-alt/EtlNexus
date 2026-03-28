import { useMemo } from "react";
import { Radio, Search } from "lucide-react";
import { useBouncers } from "@/hooks/use-bouncers";
import { useBouncerStore } from "@/stores/bouncer-store";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { TeamFilter } from "./TeamFilter";
import { BouncerCard } from "./BouncerCard";
import { BouncerTopology } from "./BouncerTopology";

export function BouncersView() {
  const teamFilter = useBouncerStore((s) => s.teamFilter);
  const selectedBouncers = useBouncerStore((s) => s.selectedBouncers);
  const clearBouncers = useBouncerStore((s) => s.clearBouncers);
  const searchQuery = useBouncerStore((s) => s.searchQuery);
  const setSearchQuery = useBouncerStore((s) => s.setSearchQuery);
  const { data, isLoading, error, refetch } = useBouncers(teamFilter);

  const filteredBouncers = useMemo(() => {
    if (!data?.bouncers) return [];
    if (!searchQuery.trim()) return data.bouncers;
    const q = searchQuery.toLowerCase();
    return data.bouncers.filter(
      (b) =>
        b.bouncer_name.toLowerCase().includes(q) ||
        b.display_name.toLowerCase().includes(q) ||
        (b.description?.toLowerCase().includes(q) ?? false),
    );
  }, [data?.bouncers, searchQuery]);

  if (isLoading) {
    return (
      <div data-section="bouncers-view" className="flex-1 flex items-center justify-center">
        <LoadingState />
      </div>
    );
  }

  if (error) {
    return (
      <div data-section="bouncers-view" className="flex-1 flex items-center justify-center">
        <ErrorState message="Failed to load bouncers" onRetry={refetch} />
      </div>
    );
  }

  if (!data || data.bouncers.length === 0) {
    return (
      <div data-section="bouncers-view" className="flex-1 flex items-center justify-center">
        <EmptyState message="No bouncers found" />
      </div>
    );
  }

  return (
    <div data-section="bouncers-view" className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="shrink-0 px-8 pt-8 pb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="bg-teal-500/10 p-2 rounded-lg border border-teal-500/20">
              <Radio className="w-5 h-5 text-teal-400" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-foreground">
                Bouncer Dashboard
              </h1>
              <p className="text-xs text-text-muted font-mono mt-0.5">
                {data.bouncers.length} bouncers across {data.teams.length} teams
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {selectedBouncers.length > 0 && (
              <button
                type="button"
                onClick={clearBouncers}
                className="text-[10px] font-mono px-3 py-1.5 rounded-lg border border-border-prominent text-text-secondary hover:text-foreground hover:border-border-prominent transition-all cursor-pointer"
              >
                Clear selection ({selectedBouncers.length})
              </button>
            )}
          </div>
        </div>

        {/* Search + Team filter */}
        <div className="flex items-center gap-3 mb-3">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
            <input
              type="text"
              placeholder="Search bouncers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-hover-bg border border-border-prominent rounded-lg text-text-primary placeholder:text-text-faint focus:outline-none focus:border-teal-500/30 transition-colors"
            />
          </div>
        </div>
        <TeamFilter teams={data.teams} />
      </div>

      {/* Main content: Split layout */}
      <div className="flex-1 flex min-h-0">
        {/* Left: Bouncer grid */}
        <div className="w-[45%] border-r border-border overflow-y-auto custom-scrollbar p-4">
          {filteredBouncers.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-sm text-text-muted">
              No bouncers match &ldquo;{searchQuery}&rdquo;
            </div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
              {filteredBouncers.map((bouncer) => (
                <BouncerCard key={bouncer.id} bouncer={bouncer} />
              ))}
            </div>
          )}
        </div>

        {/* Right: Topology */}
        <div className="w-[55%] flex flex-col min-h-0">
          <BouncerTopology />
        </div>
      </div>
    </div>
  );
}
