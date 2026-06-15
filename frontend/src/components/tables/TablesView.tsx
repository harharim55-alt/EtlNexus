import { useEffect, useMemo, useState } from "react";
import { Loader2, Search, Table2 } from "lucide-react";
import { useTables } from "@/hooks/use-tables";
import { columnsToFields, type TableSchema } from "@/types/table";
import { SchemaViewer } from "@/components/bento-workspace/SchemaViewer";
import { ConsumeSnippet } from "@/components/bento-workspace/ConsumeSnippet";

function tableKey(t: TableSchema): string {
  return `${t.namespace}.${t.table_name}`;
}

export function TablesView() {
  const { data, isLoading, isError, refetch } = useTables();
  const [search, setSearch] = useState("");
  const [teamFilter, setTeamFilter] = useState<string | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const tables = useMemo(() => data?.items ?? [], [data]);

  const teams = useMemo(() => {
    const set = new Set<string>();
    for (const t of tables) set.add(t.namespace);
    return Array.from(set).sort();
  }, [tables]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return tables.filter((t) => {
      if (teamFilter && t.namespace !== teamFilter) return false;
      if (q && !t.table_name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [tables, teamFilter, search]);

  const grouped = useMemo(() => {
    const map = new Map<string, TableSchema[]>();
    for (const t of filtered) {
      if (!map.has(t.namespace)) map.set(t.namespace, []);
      map.get(t.namespace)!.push(t);
    }
    for (const list of map.values()) list.sort((a, b) => a.table_name.localeCompare(b.table_name));
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [filtered]);

  // Keep a valid selection
  useEffect(() => {
    if (!filtered.length) {
      setSelectedKey(null);
      return;
    }
    if (!selectedKey || !filtered.some((t) => tableKey(t) === selectedKey)) {
      setSelectedKey(tableKey(filtered[0]));
    }
  }, [filtered, selectedKey]);

  const selected = filtered.find((t) => tableKey(t) === selectedKey) ?? null;

  return (
    <>
      {/* Master list */}
      <div data-section="tables-view" className="w-[400px] border-r border-border flex flex-col bg-background shrink-0">
        <div className="p-6 border-b border-border">
          <h2 className="text-xl font-medium text-foreground tracking-tight mb-4">Tables</h2>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-text-faint" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search tables..."
              className="w-full bg-card border border-border rounded-lg pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-text-faint focus:outline-none focus:border-indigo-500/50"
            />
          </div>
          {teams.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              <button
                onClick={() => setTeamFilter(null)}
                className={`text-[10px] font-mono px-2 py-0.5 rounded border transition-colors cursor-pointer ${
                  teamFilter === null
                    ? "bg-indigo-500/15 text-indigo-300 border-indigo-500/30"
                    : "bg-hover-bg text-text-muted border-border hover:text-text-secondary"
                }`}
              >
                all
              </button>
              {teams.map((team) => (
                <button
                  key={team}
                  onClick={() => setTeamFilter(team)}
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border transition-colors cursor-pointer ${
                    teamFilter === team
                      ? "bg-indigo-500/15 text-indigo-300 border-indigo-500/30"
                      : "bg-hover-bg text-text-muted border-border hover:text-text-secondary"
                  }`}
                >
                  {team}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar px-4 py-2">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="size-5 animate-spin text-text-muted" />
            </div>
          )}
          {isError && (
            <div className="flex flex-col items-center justify-center py-12 gap-2">
              <p className="text-sm text-text-muted">Failed to load tables</p>
              <button onClick={() => refetch()} className="text-xs text-indigo-400 hover:text-indigo-300 cursor-pointer">
                Retry
              </button>
            </div>
          )}
          {!isLoading && !isError && filtered.length === 0 && (
            <p className="text-sm text-text-muted text-center py-12">No tables found</p>
          )}
          {grouped.map(([team, list]) => (
            <div key={team} className="mb-2">
              <div className="sticky top-0 z-10 bg-background/90 backdrop-blur-sm px-2 py-1.5">
                <span className="text-[10px] font-mono uppercase tracking-widest text-text-faint">
                  {team} <span className="text-text-muted">({list.length})</span>
                </span>
              </div>
              {list.map((t) => {
                const key = tableKey(t);
                const active = key === selectedKey;
                return (
                  <div
                    key={key}
                    onClick={() => setSelectedKey(key)}
                    className={`group/item p-3 rounded-xl cursor-pointer transition-all border ${
                      active
                        ? "bg-card border-indigo-500/30"
                        : "bg-transparent border-transparent hover:bg-hover-bg"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <Table2 className={`size-3.5 shrink-0 ${active ? "text-indigo-400" : "text-text-muted"}`} />
                      <span className={`font-mono text-sm truncate ${active ? "text-indigo-400" : "text-text-primary"}`}>
                        {t.table_name}
                      </span>
                      <span className="ml-auto text-[10px] text-text-faint font-mono shrink-0">
                        {t.columns.length} cols
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Detail */}
      <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
        {!selected ? (
          <div className="flex-1 flex items-center justify-center h-full text-text-faint">
            <p className="text-sm font-mono">Select a table to view its schema</p>
          </div>
        ) : (
          <>
            <div className="bg-card border border-border rounded-2xl p-5 mb-6">
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-xl font-semibold text-foreground tracking-tight font-mono">
                  {selected.table_name}
                </h1>
                <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-500/[0.08] px-2.5 py-1 rounded-md border border-emerald-500/15">
                  {selected.namespace}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 lg:col-span-7">
                <SchemaViewer fields={columnsToFields(selected)} canEdit={false} />
              </div>
              <div className="col-span-12 lg:col-span-5">
                <ConsumeSnippet defaultSnippet={selected.consume_snippet} />
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
