import { useMemo, useState } from "react";
import { Check, Loader2, Search } from "lucide-react";
import { useTables } from "@/hooks/use-tables";

interface TableSelectProps {
  /** Selected tables as full names, e.g. "vault.logins". */
  value: string[];
  onChange: (next: string[]) => void;
}

const fqn = (namespace: string, table_name: string) => `${namespace}.${table_name}`;

/** Searchable multi-select of all catalog tables (any team/namespace). */
export function TableSelect({ value, onChange }: TableSelectProps) {
  const { data, isLoading } = useTables();
  const [search, setSearch] = useState("");
  const selected = useMemo(() => new Set(value), [value]);

  const tables = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (data?.items ?? []).filter(
      (t) => !q || t.table_name.toLowerCase().includes(q) || t.namespace.toLowerCase().includes(q),
    );
  }, [data, search]);

  const toggle = (name: string) => {
    if (selected.has(name)) onChange(value.filter((v) => v !== name));
    else onChange([...value, name]);
  };

  const filteredNames = useMemo(() => tables.map((t) => fqn(t.namespace, t.table_name)), [tables]);
  const allFilteredSelected = filteredNames.length > 0 && filteredNames.every((n) => selected.has(n));

  const toggleAllFiltered = () => {
    if (allFilteredSelected) {
      const drop = new Set(filteredNames);
      onChange(value.filter((v) => !drop.has(v)));
    } else {
      const additions = filteredNames.filter((n) => !selected.has(n));
      onChange([...value, ...additions]);
    }
  };

  return (
    <div className="border border-border-prominent rounded-lg overflow-hidden">
      <div className="relative border-b border-border">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-text-faint" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search tables by name or team..."
          className="w-full bg-background pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-text-faint focus:outline-none"
        />
      </div>
      {tables.length > 0 && (
        <button
          type="button"
          onClick={toggleAllFiltered}
          className="w-full text-left px-3 py-1.5 border-b border-border text-[10px] font-mono text-indigo-400 hover:bg-hover-bg transition-colors cursor-pointer"
        >
          {allFilteredSelected ? "Deselect" : "Select all"} {tables.length} filtered
        </button>
      )}
      <div className="max-h-48 overflow-y-auto custom-scrollbar">
        {isLoading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="size-4 animate-spin text-text-muted" />
          </div>
        ) : tables.length === 0 ? (
          <p className="text-xs text-text-faint text-center py-6 font-mono">No tables found</p>
        ) : (
          tables.map((t) => {
            const name = fqn(t.namespace, t.table_name);
            const isSelected = selected.has(name);
            return (
              <button
                key={name}
                type="button"
                onClick={() => toggle(name)}
                className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-hover-bg transition-colors cursor-pointer"
              >
                <span
                  className={`size-4 rounded border flex items-center justify-center shrink-0 ${
                    isSelected ? "bg-indigo-600 border-indigo-500" : "border-border-prominent"
                  }`}
                >
                  {isSelected && <Check className="size-3 text-white" />}
                </span>
                <span className="font-mono text-sm text-text-primary truncate">{t.table_name}</span>
                <span className="ml-auto text-[10px] font-mono text-emerald-400/70 shrink-0">{t.namespace}</span>
              </button>
            );
          })
        )}
      </div>
      {value.length > 0 && (
        <div className="px-3 py-2 border-t border-border text-[10px] font-mono text-text-muted">
          {value.length} table{value.length === 1 ? "" : "s"} selected
        </div>
      )}
    </div>
  );
}
