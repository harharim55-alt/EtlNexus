import { useEffect, useState } from "react";
import { Search, SlidersHorizontal } from "lucide-react";
import { usePipelineStore } from "@/stores/pipeline-store";

export function PipelineSearch() {
  const setSearchQuery = usePipelineStore((s) => s.setSearchQuery);
  const filtersOpen = usePipelineStore((s) => s.filtersOpen);
  const setFiltersOpen = usePipelineStore((s) => s.setFiltersOpen);
  const teamFilters = usePipelineStore((s) => s.teamFilters);
  const dagFilters = usePipelineStore((s) => s.dagFilters);
  const statusFilters = usePipelineStore((s) => s.statusFilters);
  const [localQuery, setLocalQuery] = useState("");

  const activeFilterCount =
    (teamFilters.size > 0 ? 1 : 0) +
    (dagFilters.size > 0 ? 1 : 0) +
    (statusFilters.size > 0 ? 1 : 0);

  // Debounce search input by 300ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchQuery(localQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [localQuery, setSearchQuery]);

  return (
    <div className="flex items-center gap-2">
      <div className="relative flex-1">
        <Search className="h-4 w-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Search pipelines or fields..."
          className="w-full bg-card border border-border-prominent rounded-lg pl-9 pr-4 py-2 text-sm text-foreground placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all"
          value={localQuery}
          onChange={(e) => setLocalQuery(e.target.value)}
        />
      </div>
      <button
        type="button"
        onClick={() => setFiltersOpen(!filtersOpen)}
        className={`relative p-2 rounded-lg border transition-all duration-200 shrink-0 cursor-pointer ${
          filtersOpen || activeFilterCount > 0
            ? "text-indigo-400 bg-indigo-500/10 border-indigo-500/25"
            : "text-text-muted bg-card border-border-prominent hover:text-text-primary hover:border-border-prominent"
        }`}
      >
        <SlidersHorizontal className="size-4" />
        {activeFilterCount > 0 && (
          <span className="absolute -top-1.5 -right-1.5 size-4 rounded-full bg-indigo-500 text-[9px] font-mono font-bold text-white flex items-center justify-center">
            {activeFilterCount}
          </span>
        )}
      </button>
    </div>
  );
}
