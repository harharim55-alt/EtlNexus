import { useEffect, useMemo, useCallback, useState } from "react";
import { useDataProducts } from "@/hooks/use-data-products";
import { useDataProductStore } from "@/stores/data-product-store";
import { useFavoritesStore } from "@/stores/favorites-store";
import { DataProductSearch } from "./DataProductSearch";
import { DataProductFilters } from "./DataProductFilters";
import { DataProductListItem } from "./DataProductListItem";
import { CreateDataProductModal } from "./CreateDataProductModal";

import { Plus, X } from "lucide-react";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import type { PipelineListItem as PipelineListItemType } from "@/types/pipeline";
import type { PipelineFilterParams } from "@/api/pipelines";
import { Loader2 } from "lucide-react";

interface CategoryGroup {
  category: string;
  pipelines: PipelineListItemType[];
}

export function DataProductRegistry() {
  const {
    searchQuery,
    selectedProductId,
    setSelectedProductId,
    filtersOpen,
    teamFilters,
    networkFilters,
    tagFilters,
    clearAllFilters,
  } = useDataProductStore();

  const [createOpen, setCreateOpen] = useState(false);

  const serverFilters = useMemo<PipelineFilterParams | undefined>(() => {
    const f: PipelineFilterParams = {};
    if (teamFilters.size > 0) f.team = Array.from(teamFilters);
    if (tagFilters.size > 0) f.tag = Array.from(tagFilters);
    return Object.keys(f).length > 0 ? f : undefined;
  }, [teamFilters, tagFilters]);

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    refetch,
  } = useDataProducts(searchQuery, serverFilters);

  const products = useMemo(
    () => data?.pages.flatMap((p) => p.items) ?? [],
    [data],
  );

  const hasActiveFilters =
    teamFilters.size > 0 || networkFilters.size > 0 || tagFilters.size > 0;

  const availableTeams = useMemo(() => {
    const teams = new Set<string>();
    for (const p of products) {
      if (p.team) teams.add(p.team);
    }
    return Array.from(teams).sort();
  }, [products]);

  const availableTags = useMemo(() => {
    const tags = new Set<string>();
    for (const p of products) {
      for (const t of (p.tags ?? [])) tags.add(t.name);
    }
    return Array.from(tags).sort();
  }, [products]);

  const availableNetworks = useMemo(() => {
    const nets = new Set<string>();
    for (const p of products) {
      for (const n of (p.network_names ?? [])) nets.add(n);
    }
    return Array.from(nets).sort();
  }, [products]);

  // Client-side tag/network filtering
  const filteredProducts = useMemo(() => {
    if (!products.length) return [];
    if (!hasActiveFilters) return products;

    return products.filter((p) => {
      if (teamFilters.size > 0 && (!p.team || !teamFilters.has(p.team))) return false;
      if (networkFilters.size > 0) {
        const pNets = new Set(p.network_names ?? []);
        let hasAny = false;
        for (const net of networkFilters) {
          if (pNets.has(net)) { hasAny = true; break; }
        }
        if (!hasAny) return false;
      }
      if (tagFilters.size > 0) {
        const pTags = new Set((p.tags ?? []).map((t) => t.name));
        let hasAny = false;
        for (const tag of tagFilters) {
          if (pTags.has(tag)) { hasAny = true; break; }
        }
        if (!hasAny) return false;
      }
      return true;
    });
  }, [products, teamFilters, networkFilters, tagFilters, hasActiveFilters]);

  const favoriteIds = useFavoritesStore((s) => s.favoriteIds);

  const groupedProducts = useMemo<CategoryGroup[]>(() => {
    if (!filteredProducts.length) return [];

    const result: CategoryGroup[] = [];
    const favSet = new Set(favoriteIds);
    const favProducts = filteredProducts.filter((p) => favSet.has(p.id));
    if (favProducts.length > 0) {
      result.push({ category: "\u2605 Favorites", pipelines: favProducts });
    }

    // Group by team
    const groups = new Map<string, PipelineListItemType[]>();
    for (const product of filteredProducts) {
      const group = product.team || "Unassigned";
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group)!.push(product);
    }

    for (const items of groups.values()) {
      items.sort((a, b) => a.name.localeCompare(b.name));
    }

    const sorted = Array.from(groups.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([category, pipelines]) => ({ category, pipelines }));

    result.push(...sorted);
    return result;
  }, [filteredProducts, favoriteIds]);

  useEffect(() => {
    if (groupedProducts.length > 0 && !selectedProductId) {
      setSelectedProductId(groupedProducts[0].pipelines[0].id);
    }
  }, [groupedProducts, selectedProductId, setSelectedProductId]);

  useEffect(() => {
    if (!selectedProductId || !filteredProducts.length) return;
    const stillVisible = filteredProducts.some((p) => p.id === selectedProductId);
    if (!stillVisible) {
      setSelectedProductId(filteredProducts[0].id);
    }
  }, [filteredProducts, selectedProductId, setSelectedProductId]);

  const filterSummary = useMemo(() => {
    if (!hasActiveFilters) return null;
    const parts: string[] = [];
    if (teamFilters.size > 0) parts.push(Array.from(teamFilters).join(", "));
    if (networkFilters.size > 0) parts.push(Array.from(networkFilters).join(", "));
    if (tagFilters.size > 0) parts.push(Array.from(tagFilters).join(", "));
    return parts.join(" \u00b7 ");
  }, [hasActiveFilters, teamFilters, networkFilters, tagFilters]);

  const isFiltered = hasActiveFilters && products.length > 0 && filteredProducts.length !== products.length;

  const handleSelectProduct = useCallback(
    (id: string) => setSelectedProductId(id),
    [setSelectedProductId],
  );

  return (
    <>
      <div data-section="data-products-registry" className="w-[400px] border-r border-border flex flex-col bg-background shrink-0">
        <div className="p-6 border-b border-border">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-medium text-foreground tracking-tight">
              Data Products
            </h2>
            <div className="flex items-center gap-1">
              <Tooltip>
                <TooltipTrigger
                  className="p-1.5 text-text-muted hover:text-foreground rounded-lg transition-colors cursor-pointer"
                  onClick={() => setCreateOpen(true)}
                >
                  <Plus className="size-4" />
                </TooltipTrigger>
                <TooltipContent>New Data Product</TooltipContent>
              </Tooltip>
            </div>
          </div>
          <DataProductSearch />
        </div>

        {/* Filter drawer */}
        <div
          className="grid transition-all duration-200 border-b"
          style={{
            gridTemplateRows: filtersOpen ? "1fr" : "0fr",
            opacity: filtersOpen ? 1 : 0,
            borderColor: filtersOpen ? "rgba(255,255,255,0.05)" : "transparent",
          }}
        >
          <div className="overflow-hidden">
            <DataProductFilters
              availableTeams={availableTeams}
              availableNetworks={availableNetworks}
              availableTags={availableTags}
            />
          </div>
        </div>

        {/* Active filter strip */}
        {!filtersOpen && hasActiveFilters && (
          <div className="px-6 py-2 border-b border-border flex items-center gap-2 animate-in fade-in duration-150">
            <span className="text-[10px] font-mono text-text-muted truncate flex-1">
              <span className="text-text-faint">Filtered:</span>{" "}
              <span className="text-indigo-400">{filterSummary}</span>
            </span>
            <button
              type="button"
              onClick={clearAllFilters}
              className="text-text-faint hover:text-text-secondary transition-colors cursor-pointer shrink-0"
            >
              <X className="size-3" />
            </button>
          </div>
        )}

        {isFiltered && (
          <div className="px-6 py-1.5">
            <span className="text-[10px] font-mono text-text-faint">
              Showing {filteredProducts.length} of {products.length}
            </span>
          </div>
        )}

        {/* Product list */}
        <div className="flex-1 overflow-y-auto custom-scrollbar px-4 py-2">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="size-5 animate-spin text-text-muted" />
            </div>
          )}
          {isError && (
            <div className="flex flex-col items-center justify-center py-12 gap-2">
              <p className="text-sm text-text-muted">Failed to load data products</p>
              <button
                onClick={() => refetch()}
                className="text-xs text-indigo-400 hover:text-indigo-300 cursor-pointer"
              >
                Retry
              </button>
            </div>
          )}
          {!isLoading && !isError && groupedProducts.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 gap-2">
              <p className="text-sm text-text-muted">No data products found</p>
              <button
                onClick={() => setCreateOpen(true)}
                className="text-xs text-indigo-400 hover:text-indigo-300 cursor-pointer"
              >
                Create your first data product
              </button>
            </div>
          )}
          {groupedProducts.map((group) => (
            <div key={group.category} className="mb-2">
              <div className="sticky top-0 z-10 bg-background/90 backdrop-blur-sm px-2 py-1.5">
                <span className="text-[10px] font-mono uppercase tracking-widest text-text-faint">
                  {group.category}{" "}
                  <span className="text-text-muted">({group.pipelines.length})</span>
                </span>
              </div>
              {group.pipelines.map((product) => (
                <DataProductListItem
                  key={product.id}
                  product={product}
                  isActive={product.id === selectedProductId}
                  onClick={() => handleSelectProduct(product.id)}
                />
              ))}
            </div>
          ))}
          {hasNextPage && (
            <button
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
              className="w-full py-3 text-xs text-indigo-400 hover:text-indigo-300 font-mono cursor-pointer"
            >
              {isFetchingNextPage ? "Loading..." : "Load more"}
            </button>
          )}
        </div>
      </div>

      <CreateDataProductModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(product) => {
          setCreateOpen(false);
          setSelectedProductId(product.id);
        }}
      />
    </>
  );
}
