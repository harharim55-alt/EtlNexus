import { useCallback, useEffect, useRef, useState } from "react";
import { Package, Search } from "lucide-react";
import { fetchPipelines } from "@/api/pipelines";
import { useNavigationStore } from "@/stores/navigation-store";
import { useDataProductStore } from "@/stores/data-product-store";
import { stripDummy } from "@/lib/format";
import type { PipelineListItem } from "@/types/pipeline";

interface SearchResult {
  id: string;
  productId: string;
  label: string;
  sublabel?: string;
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
  const setSelectedProductId = useDataProductStore((s) => s.setSelectedProductId);

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

  const selectResult = useCallback(
    (productId: string) => {
      setActiveTab("data-products");
      setSelectedProductId(productId);
      close();
    },
    [setActiveTab, setSelectedProductId, close],
  );

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
      try {
        const res = await fetchPipelines(query, 0, 12);
        setResults(
          res.items.map((p: PipelineListItem) => ({
            id: `product-${p.id}`,
            productId: p.id,
            label: stripDummy(p.name),
            sublabel: p.team ?? undefined,
          })),
        );
      } catch {
        setResults([]);
      }
      setActiveIndex(0);
      setLoading(false);
    }, 200);
  }, [query, open]);

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
      selectResult(results[activeIndex].productId);
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

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      <div className="absolute inset-0 bg-black/60" onClick={close} />

      <div className="relative w-full max-w-lg bg-card border border-border-prominent rounded-xl shadow-2xl overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
          <Search className="size-4 text-text-muted shrink-0" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search data products..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-text-faint outline-none"
          />
          <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-raised text-text-muted border border-border">
            ESC
          </kbd>
        </div>

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
              {results.map((item, idx) => (
                <button
                  key={item.id}
                  type="button"
                  className={`w-full flex items-center gap-3 px-4 py-2 text-left transition-colors cursor-pointer ${
                    idx === activeIndex
                      ? "bg-primary/10 text-foreground"
                      : "text-text-primary hover:bg-hover-bg"
                  }`}
                  onClick={() => selectResult(item.productId)}
                  onMouseEnter={() => setActiveIndex(idx)}
                >
                  <Package className="size-4 text-indigo-400" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm truncate">{item.label}</div>
                    {item.sublabel && (
                      <div className="text-xs text-text-muted truncate">{item.sublabel}</div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}

          {!query.trim() && (
            <div className="px-4 py-6 text-sm text-text-muted text-center">
              Type to search data products
            </div>
          )}
        </div>

        <div className="flex items-center gap-4 px-4 py-2 border-t border-border text-[10px] text-text-faint font-mono">
          <span><kbd className="px-1 py-0.5 rounded bg-surface-raised border border-border">↑↓</kbd> navigate</span>
          <span><kbd className="px-1 py-0.5 rounded bg-surface-raised border border-border">↵</kbd> select</span>
          <span><kbd className="px-1 py-0.5 rounded bg-surface-raised border border-border">esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}
