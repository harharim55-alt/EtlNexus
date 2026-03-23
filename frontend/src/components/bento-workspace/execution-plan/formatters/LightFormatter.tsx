import {
  Merge,
  ChevronsDownUp,
  ListEnd,
  Layers,
  Sparkles,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

/**
 * Lightweight formatter for simple plan nodes:
 * Union, Limit, GlobalLimit, LocalLimit, TakeOrderedAndProject,
 * Expand, Coalesce, Generate.
 */
export function LightFormatter({ node }: { node: ExecutionPlanNode }) {
  const lower = node.name.toLowerCase();
  const detail = node.full_detail || node.detail;

  // Union
  if (lower === "union") {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2.5">
          <Merge className="w-4 h-4 text-cyan-400 shrink-0" />
          <span className="text-sm font-semibold text-cyan-300 font-mono">
            Union
          </span>
          <span className="text-[10px] font-mono text-slate-500 bg-white/5 px-1.5 py-0.5 rounded">
            {node.children.length} branches
          </span>
        </div>
        <MetricsBar metrics={node.metrics} />
      </div>
    );
  }

  // Limit variants + TakeOrderedAndProject
  if (lower.includes("limit") || lower === "takeorderedandproject") {
    // Parse "limit N | order by col DESC" format from backend
    const sections = detail.split("|").map((s) => s.trim());
    let limit = "";
    let orderBy: { column: string; direction: "ASC" | "DESC" }[] = [];

    for (const section of sections) {
      if (section.startsWith("limit ")) {
        limit = section.replace("limit ", "");
      } else if (section.startsWith("order by ")) {
        orderBy = section
          .replace("order by ", "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
          .map((part) => ({
            column: part.replace(/\s*(ASC|DESC).*/, ""),
            direction: part.includes("DESC") ? "DESC" : "ASC",
          }));
      }
    }

    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2.5">
          <ListEnd className="w-4 h-4 text-teal-400 shrink-0" />
          <span className="text-sm font-semibold text-teal-300 font-mono">
            {node.name.replace(/([a-z])([A-Z])/g, "$1 $2")}
          </span>
          {limit && (
            <span className="text-[10px] font-mono font-bold text-teal-300 bg-teal-500/10 border border-teal-500/20 rounded-md px-2 py-0.5">
              {limit} rows
            </span>
          )}
        </div>
        {orderBy.length > 0 && (
          <div className="space-y-1.5">
            {orderBy.map((k, i) => (
              <div
                key={i}
                className="flex items-center gap-2 px-3 py-2 bg-black/20 rounded-lg border border-white/[0.04]"
              >
                {k.direction === "ASC" ? (
                  <ChevronUp className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                )}
                <span className="text-xs font-mono text-slate-300">
                  {k.column}
                </span>
                <span className="text-[9px] font-mono text-slate-600 ml-auto">
                  {k.direction}
                </span>
              </div>
            ))}
          </div>
        )}
        <MetricsBar metrics={node.metrics} />
      </div>
    );
  }

  // Coalesce
  if (lower === "coalesce") {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2.5">
          <ChevronsDownUp className="w-4 h-4 text-orange-400 shrink-0" />
          <span className="text-sm font-semibold text-orange-300 font-mono">
            Coalesce
          </span>
          {detail && (
            <span className="text-[10px] font-mono text-orange-300 bg-orange-500/10 border border-orange-500/20 rounded-md px-2 py-0.5">
              {detail}
            </span>
          )}
        </div>
        <MetricsBar metrics={node.metrics} />
      </div>
    );
  }

  // Expand
  if (lower === "expand") {
    const items = detail
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2.5">
          <Layers className="w-4 h-4 text-purple-400 shrink-0" />
          <span className="text-sm font-semibold text-purple-300 font-mono">
            Expand
          </span>
        </div>
        {items.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {items.map((item, i) => (
              <span
                key={i}
                className="text-[11px] font-mono text-purple-300 bg-purple-500/10 border border-purple-500/20 rounded-md px-2 py-0.5"
              >
                {item}
              </span>
            ))}
          </div>
        )}
        <MetricsBar metrics={node.metrics} />
      </div>
    );
  }

  // Generate (explode, etc.)
  if (lower === "generate") {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2.5">
          <Sparkles className="w-4 h-4 text-pink-400 shrink-0" />
          <span className="text-sm font-semibold text-pink-300 font-mono">
            Generate
          </span>
          {detail && (
            <span className="text-[10px] font-mono text-pink-300 bg-pink-500/10 border border-pink-500/20 rounded-md px-2 py-0.5">
              {detail}
            </span>
          )}
        </div>
        <MetricsBar metrics={node.metrics} />
      </div>
    );
  }

  // Fallback for anything else routed here
  return (
    <div className="space-y-4">
      {detail && (
        <div className="text-xs font-mono text-slate-300 bg-black/30 p-3 rounded-lg break-all leading-relaxed">
          {detail}
        </div>
      )}
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
