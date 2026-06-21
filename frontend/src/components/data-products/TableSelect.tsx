import { useMemo, useState } from "react";
import { Check, Loader2, Search } from "lucide-react";
import { useTables } from "@/hooks/use-tables";

export interface TableRef {
  namespace: string;
  table_name: string;
}

interface TableSelectProps {
  value: TableRef[];
  onChange: (next: TableRef[]) => void;
}

const keyOf = (t: TableRef) => `${t.namespace}.${t.table_name}`;

/** Searchable multi-select of all catalog tables (any team/namespace). */
export function TableSelect({ value, onChange }: TableSelectProps) {
  const { data, isLoading } = useTables();
  const [search, setSearch] = useState("");
  const selectedKeys = useMemo(() => new Set(value.map(keyOf)), [value]);

  const tables = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (data?.items ?? []).filter(
      (t) => !q || t.table_name.toLowerCase().includes(q) || t.namespace.toLowerCase().includes(q),
    );
  }, [data, search]);

  const toggle = (t: TableRef) => {
    if (selectedKeys.has(keyOf(t))) {
      onChange(value.filter((v) => keyOf(v) !== keyOf(t)));
    } else {
      onChange([...value, { namespace: t.namespace, table_name: t.table_name }]);
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
      <div className="max-h-48 overflow-y-auto custom-scrollbar">
        {isLoading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="size-4 animate-spin text-text-muted" />
          </div>
        ) : tables.length === 0 ? (
          <p className="text-xs text-text-faint text-center py-6 font-mono">No tables found</p>
        ) : (
          tables.map((t) => {
            const selected = selectedKeys.has(keyOf(t));
            return (
              <button
                key={keyOf(t)}
                type="button"
                onClick={() => toggle(t)}
                className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-hover-bg transition-colors cursor-pointer"
              >
                <span
                  className={`size-4 rounded border flex items-center justify-center shrink-0 ${
                    selected ? "bg-indigo-600 border-indigo-500" : "border-border-prominent"
                  }`}
                >
                  {selected && <Check className="size-3 text-white" />}
                </span>
                <span className="font-mono text-sm text-text-primary truncate">{t.table_name}</span>
                <span className="ml-auto text-[10px] font-mono text-emerald-400/70 shrink-0">{t.namespace}</span>
                <span className="text-[10px] text-text-faint font-mono shrink-0">{t.columns.length}c</span>
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
