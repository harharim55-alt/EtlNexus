import { useEffect, useState } from "react";
import { Search, SlidersHorizontal } from "lucide-react";
import { useDataProductStore } from "@/stores/data-product-store";

export function DataProductSearch() {
  const setSearchQuery = useDataProductStore((s) => s.setSearchQuery);
  const filtersOpen = useDataProductStore((s) => s.filtersOpen);
  const setFiltersOpen = useDataProductStore((s) => s.setFiltersOpen);
  const teamFilters = useDataProductStore((s) => s.teamFilters);
  const networkFilters = useDataProductStore((s) => s.networkFilters);
  const tagFilters = useDataProductStore((s) => s.tagFilters);
  const [localQuery, setLocalQuery] = useState("");

  const activeFilterCount =
    (teamFilters.size > 0 ? 1 : 0) +
    (networkFilters.size > 0 ? 1 : 0) +
    (tagFilters.size > 0 ? 1 : 0);

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
          placeholder="Search data products..."
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
