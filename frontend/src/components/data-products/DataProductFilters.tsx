import { useDataProductStore } from "@/stores/data-product-store";
import { X } from "lucide-react";

const INACTIVE_PILL =
  "text-text-muted bg-hover-bg border-border hover:border-border-prominent hover:text-text-secondary";

interface DataProductFiltersProps {
  availableTeams: string[];
  availableNetworks: string[];
  availableTags: string[];
}

export function DataProductFilters({ availableTeams, availableNetworks, availableTags }: DataProductFiltersProps) {
  const { teamFilters, networkFilters, tagFilters, toggleFilter, clearAllFilters } =
    useDataProductStore();

  const hasActive = teamFilters.size > 0 || networkFilters.size > 0 || tagFilters.size > 0;

  return (
    <div className="px-5 pb-4 pt-1 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono uppercase tracking-widest text-text-faint">
          Filters
        </span>
        {hasActive && (
          <button
            type="button"
            onClick={clearAllFilters}
            className="text-[10px] font-mono text-text-muted hover:text-indigo-400 transition-colors cursor-pointer flex items-center gap-1"
          >
            <X className="size-3" />
            Clear all
          </button>
        )}
      </div>

      {availableTeams.length > 0 && (
        <FilterSection label="Team">
          {availableTeams.map((team) => (
            <button
              key={team}
              type="button"
              onClick={() => toggleFilter("team", team)}
              className={`text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer ${
                teamFilters.has(team)
                  ? "text-indigo-300 bg-indigo-500/15 border-indigo-500/30"
                  : INACTIVE_PILL
              }`}
            >
              {team}
            </button>
          ))}
        </FilterSection>
      )}

      {availableNetworks.length > 0 && (
        <FilterSection label="Network">
          {availableNetworks.map((network) => (
            <button
              key={network}
              type="button"
              onClick={() => toggleFilter("network", network)}
              className={`text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer ${
                networkFilters.has(network)
                  ? "text-teal-300 bg-teal-500/15 border-teal-500/30"
                  : INACTIVE_PILL
              }`}
            >
              {network}
            </button>
          ))}
        </FilterSection>
      )}

      {availableTags.length > 0 && (
        <FilterSection label="Tag">
          {availableTags.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => toggleFilter("tag", tag)}
              className={`text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer ${
                tagFilters.has(tag)
                  ? "text-amber-300 bg-amber-500/15 border-amber-500/30"
                  : INACTIVE_PILL
              }`}
            >
              {tag}
            </button>
          ))}
        </FilterSection>
      )}
    </div>
  );
}

function FilterSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <span className="text-[9px] font-mono uppercase tracking-widest text-text-faint">
          {label}
        </span>
        <div className="flex-1 h-px bg-hover-bg" />
      </div>
      <div className="flex items-center gap-1.5 flex-wrap">{children}</div>
    </div>
  );
}
