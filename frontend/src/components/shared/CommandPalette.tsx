import { useCallback, useEffect, useRef, useState } from "react";
import { Database, Radio, Search, BarChart3 } from "lucide-react";
import { fetchPipelines } from "@/api/pipelines";
import { fetchBouncers } from "@/api/bouncers";
import { fetchDagSummary } from "@/api/dag-summary";
import { useNavigationStore } from "@/stores/navigation-store";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useBouncerStore } from "@/stores/bouncer-store";
import { stripDummy } from "@/lib/format";
import type { PipelineListItem } from "@/types/pipeline";

interface SearchResult {
  id: string;
  label: string;
  sublabel?: string;
  icon: React.ReactNode;
  category: "pipeline" | "dag" | "bouncer";
  action: () => void;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const setActiveTab = useNavigationStore((s) => s.setActiveTab);
  const setSelectedPipelineId = usePipelineStore((s) => s.setSelectedPipelineId);

  // Open/close with Cmd+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  // Focus input on open
  useEffect(() => {
    if (open) {
      setQuery("");
      setResults([]);
      setActiveIndex(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
    setResults([]);
  }, []);

  // Search on query change
  useEffect(() => {
    if (!open) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!query.trim()) {
      setResults([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      const q = query.toLowerCase();
      const items: SearchResult[] = [];

      try {
        const [pipelineRes, bouncerRes, dagRes] = await Promise.allSettled([
          fetchPipelines(query, 0, 8),
          fetchBouncers(undefined),
          fetchDagSummary(undefined),
        ]);

        if (pipelineRes.status === "fulfilled") {
          pipelineRes.value.items.forEach((p: PipelineListItem) => {
            items.push({
              id: `pipeline-${p.id}`,
              label: stripDummy(p.name),
              sublabel: [p.pipeline_type?.toUpperCase(), p.team].filter(Boolean).join(" · "),
              icon: <Database className="size-4 text-indigo-400" />,
              category: "pipeline",
              action: () => {
                setActiveTab("catalog");
                setSelectedPipelineId(p.id);
                close();
              },
            });
          });
        }

        if (bouncerRes.status === "fulfilled") {
          bouncerRes.value.bouncers
            .filter((b) =>
              b.bouncer_name.toLowerCase().includes(q) ||
              b.display_name.toLowerCase().includes(q) ||
              (b.description?.toLowerCase().includes(q) ?? false),
            )
            .slice(0, 5)
            .forEach((b) => {
              items.push({
                id: `bouncer-${b.id}`,
                label: b.display_name,
                sublabel: b.team ?? undefined,
                icon: <Radio className="size-4 text-teal-400" />,
                category: "bouncer",
                action: () => {
                  setActiveTab("bouncers");
                  useBouncerStore.getState().toggleBouncer(b.bouncer_name);
                  close();
                },
              });
            });
        }

        if (dagRes.status === "fulfilled") {
          dagRes.value.dags
            .filter((d) => d.dag_id.toLowerCase().includes(q))
            .slice(0, 5)
            .forEach((d) => {
              items.push({
                id: `dag-${d.dag_id}`,
                label: d.dag_id,
                sublabel: `${d.pipeline_count} pipelines`,
                icon: <BarChart3 className="size-4 text-amber-400" />,
                category: "dag",
                action: () => {
                  setActiveTab("dags");
                  close();
                },
              });
            });
        }
      } catch {
        // Ignore fetch errors in search
      }

      setResults(items);
      setActiveIndex(0);
      setLoading(false);
    }, 200);
  }, [query, open, close, setActiveTab, setSelectedPipelineId]);

  // Keyboard navigation
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results[activeIndex]) {
      e.preventDefault();
      results[activeIndex].action();
    }
  };

  // Scroll active item into view
  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const active = list.children[activeIndex] as HTMLElement;
    active?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  if (!open) return null;

  const grouped = {
    pipeline: results.filter((r) => r.category === "pipeline"),
    bouncer: results.filter((r) => r.category === "bouncer"),
    dag: results.filter((r) => r.category === "dag"),
  };

  let globalIdx = -1;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={close} />

      {/* Palette */}
      <div className="relative w-full max-w-lg bg-card border border-border-prominent rounded-xl shadow-2xl overflow-hidden">
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
          <Search className="size-4 text-text-muted shrink-0" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search pipelines, DAGs, bouncers..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-text-faint outline-none"
          />
          <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-raised text-text-muted border border-border">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-80 overflow-y-auto custom-scrollbar">
          {loading && query.trim() && (
            <div className="px-4 py-6 text-sm text-text-muted text-center">Searching...</div>
          )}

          {!loading && query.trim() && results.length === 0 && (
            <div className="px-4 py-6 text-sm text-text-muted text-center">
              No results for &ldquo;{query}&rdquo;
            </div>
          )}

          {!loading && results.length > 0 && (
            <div className="py-2">
              {(["pipeline", "bouncer", "dag"] as const).map((cat) => {
                const items = grouped[cat];
                if (items.length === 0) return null;
                const catLabel = cat === "pipeline" ? "Pipelines" : cat === "bouncer" ? "Bouncers" : "DAGs";
                return (
                  <div key={cat}>
                    <div className="px-4 py-1.5 text-[10px] font-mono uppercase tracking-widest text-text-faint">
                      {catLabel}
                    </div>
                    {items.map((item) => {
                      globalIdx++;
                      const idx = globalIdx;
                      return (
                        <button
                          key={item.id}
                          type="button"
                          className={`w-full flex items-center gap-3 px-4 py-2 text-left transition-colors cursor-pointer ${
                            idx === activeIndex
                              ? "bg-primary/10 text-foreground"
                              : "text-text-primary hover:bg-hover-bg"
                          }`}
                          onClick={item.action}
                          onMouseEnter={() => setActiveIndex(idx)}
                        >
                          {item.icon}
                          <div className="flex-1 min-w-0">
                            <div className="text-sm truncate">{item.label}</div>
                            {item.sublabel && (
                              <div className="text-xs text-text-muted truncate">{item.sublabel}</div>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          )}

          {!query.trim() && (
            <div className="px-4 py-6 text-sm text-text-muted text-center">
              Type to search across pipelines, DAGs, and bouncers
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-border text-[10px] text-text-faint font-mono">
          <span><kbd className="px-1 py-0.5 rounded bg-surface-raised border border-border">↑↓</kbd> navigate</span>
          <span><kbd className="px-1 py-0.5 rounded bg-surface-raised border border-border">↵</kbd> select</span>
          <span><kbd className="px-1 py-0.5 rounded bg-surface-raised border border-border">esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}
