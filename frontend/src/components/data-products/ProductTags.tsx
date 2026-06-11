import { useState } from "react";
import { Tag as TagIcon, Plus, X } from "lucide-react";
import { useTags, useSetPipelineTags } from "@/hooks/use-tags";
import { useDataProductStore } from "@/stores/data-product-store";
import { stripDummy } from "@/lib/format";
import type { Tag } from "@/types/pipeline";

interface ProductTagsProps {
  productId: string;
  /** Tags currently applied to the product (from PipelineDetail.tags). */
  tags: Tag[];
  canEdit: boolean;
}

/** Tag chips on a regular product page. Chips link to the tag's page; editors
 *  can add any existing tag or remove an applied one. */
export function ProductTags({ productId, tags, canEdit }: ProductTagsProps) {
  const setSelectedProductId = useDataProductStore((s) => s.setSelectedProductId);
  const { data: allTags } = useTags();
  const { mutate: saveTags, isPending } = useSetPipelineTags(productId);
  const [adding, setAdding] = useState(false);

  const appliedIds = new Set(tags.map((t) => t.id));
  const available = (allTags?.items ?? []).filter((t) => !appliedIds.has(t.id));

  const apply = (next: string[]) => saveTags(next);
  const addTag = (tagId: string) => {
    apply([...tags.map((t) => t.id), tagId]);
    setAdding(false);
  };
  const removeTag = (tagId: string) => apply(tags.filter((t) => t.id !== tagId).map((t) => t.id));

  if (!canEdit && tags.length === 0) return null;

  return (
    <div className="bg-card border border-border rounded-2xl p-5">
      <h3 className="text-[11px] font-mono uppercase tracking-widest text-text-muted flex items-center gap-2 mb-3">
        <TagIcon className="w-3.5 h-3.5" /> Tags
      </h3>
      <div className="flex items-center gap-2 flex-wrap">
        {tags.map((tag) => (
          <span
            key={tag.id}
            className="group/chip flex items-center gap-1 text-[11px] font-mono text-amber-300 bg-amber-500/10 px-2 py-1 rounded-md border border-amber-500/20"
          >
            <button
              type="button"
              onClick={() => setSelectedProductId(tag.id)}
              className="hover:text-amber-200 transition-colors cursor-pointer"
              title="Open tag"
            >
              {stripDummy(tag.name)}
            </button>
            {canEdit && (
              <button
                type="button"
                onClick={() => removeTag(tag.id)}
                disabled={isPending}
                className="text-amber-300/50 hover:text-amber-200 transition-colors cursor-pointer"
                title="Remove tag"
              >
                <X className="size-3" />
              </button>
            )}
          </span>
        ))}

        {tags.length === 0 && !adding && (
          <span className="text-xs text-text-faint font-mono">No tags applied</span>
        )}

        {canEdit && !adding && available.length > 0 && (
          <button
            type="button"
            onClick={() => setAdding(true)}
            className="flex items-center gap-1 text-[11px] font-mono text-text-muted hover:text-indigo-400 border border-dashed border-border hover:border-indigo-500/40 px-2 py-1 rounded-md transition-colors cursor-pointer"
          >
            <Plus className="size-3" /> Add tag
          </button>
        )}

        {canEdit && adding && (
          <select
            autoFocus
            defaultValue=""
            disabled={isPending}
            onChange={(e) => e.target.value && addTag(e.target.value)}
            onBlur={() => setAdding(false)}
            className="bg-background border border-border-prominent rounded-md px-2 py-1 text-xs text-foreground focus:outline-none focus:border-indigo-500/50"
          >
            <option value="">Select a tag...</option>
            {available.map((t) => (
              <option key={t.id} value={t.id}>
                {stripDummy(t.name)}
              </option>
            ))}
          </select>
        )}
      </div>
    </div>
  );
}
