import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { usePipelineStore } from "@/stores/pipeline-store";

export function PipelineSearch() {
  const setSearchQuery = usePipelineStore((s) => s.setSearchQuery);
  const [localQuery, setLocalQuery] = useState("");

  // Debounce search input by 300ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchQuery(localQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [localQuery, setSearchQuery]);

  return (
    <div className="relative">
      <Search className="h-4 w-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
      <input
        type="text"
        placeholder="Search pipelines or fields..."
        className="w-full bg-[#18181b] border border-white/10 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all"
        value={localQuery}
        onChange={(e) => setLocalQuery(e.target.value)}
      />
    </div>
  );
}
