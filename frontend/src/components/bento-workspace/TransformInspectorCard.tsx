import { useState, useRef, useEffect } from "react";
import {
  GitMerge,
  Database,
  HardDrive,
  ArrowRightLeft,
  Activity,
  Maximize2,
  X,
  ArrowRight,
  ChevronUp,
  ChevronDown,
  Columns3,
  Filter as FilterIcon,
  Shuffle,
  Table2,
  Loader2,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useExecutionPlan, useExecutionPlanRuns } from "@/hooks/use-execution-plan";
import type { ExecutionPlanNode } from "@/types/execution-plan";

interface TransformInspectorCardProps {
  pipelineId: string;
}

const NODE_STYLES: Record<
  ExecutionPlanNode["type"],
  {
    bg: string;
    border: string;
    text: string;
    icon: typeof Database;
  }
> = {
  read: {
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
    text: "text-blue-400",
    icon: Database,
  },
  write: {
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
    text: "text-emerald-400",
    icon: HardDrive,
  },
  shuffle: {
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    text: "text-amber-400",
    icon: ArrowRightLeft,
  },
  transform: {
    bg: "bg-indigo-500/10",
    border: "border-indigo-500/30",
    text: "text-indigo-400",
    icon: Activity,
  },
};

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins < 60) return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  const hrs = Math.floor(mins / 60);
  const remainMins = mins % 60;
  return remainMins > 0 ? `${hrs}h ${remainMins}m` : `${hrs}h`;
}

// Metrics that get prominent display with ⏱ icon
const TIME_KEYS = new Set([
  "scan time",
  "build time",
  "stream time",
  "sort time",
  "agg time",
  "plan time",
  "metadata",
]);

// Metrics to hide (low-value noise for cards)
const HIDDEN_KEYS = new Set(["data files", "files"]);

function NodeCard({
  node,
  onExpand,
}: {
  node: ExecutionPlanNode;
  onExpand: (node: ExecutionPlanNode) => void;
}) {
  const style = NODE_STYLES[node.type] ?? NODE_STYLES.transform;
  const Icon = style.icon;
  const entries = Object.entries(node.metrics);
  const rows = node.metrics.rows;
  const timeEntry = entries.find(([k]) => TIME_KEYS.has(k));
  const rest = entries.filter(
    ([k]) => k !== "rows" && !TIME_KEYS.has(k) && !HIDDEN_KEYS.has(k),
  );
  const hasContent = node.detail || entries.length > 0;

  return (
    <div
      className={`group/card relative inline-flex flex-col gap-1.5 px-4 py-3 rounded-xl border ${style.bg} ${style.border} min-w-[170px] max-w-[260px]`}
    >
      {hasContent && (
        <button
          onClick={() => onExpand(node)}
          className="absolute top-2 right-2 p-1 rounded-md opacity-0 group-hover/card:opacity-100 transition-opacity text-slate-500 hover:text-slate-300 hover:bg-white/5"
          title="Expand details"
        >
          <Maximize2 className="w-3 h-3" />
        </button>
      )}
      <div className="flex items-center gap-2">
        <Icon className={`w-3.5 h-3.5 shrink-0 ${style.text}`} />
        <span className={`text-xs font-semibold truncate ${style.text}`}>
          {node.name}
        </span>
      </div>
      {node.detail && (
        <span
          className="text-[10px] font-mono text-slate-400 leading-tight line-clamp-2"
          title={node.detail}
        >
          {node.detail}
        </span>
      )}
      {entries.length > 0 && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-0.5 border-t border-white/5 pt-1.5">
          {timeEntry && (
            <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
              <span className="text-slate-600">⏱</span>
              {timeEntry[1]}
            </span>
          )}
          {rows && (
            <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
              <span className="text-slate-600">≣</span>
              {rows}
            </span>
          )}
          {rest.map(([key, val]) => (
            <span
              key={key}
              className="text-[9px] font-mono text-slate-500"
            >
              <span className="text-slate-600">{key}:</span>{" "}
              <span className="text-slate-400">{val}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Detail parsing helpers ───────────────────────────────────────

function parseScanDetail(detail: string): {
  table: string;
  columns: string[];
} {
  const m = detail.match(/^(\S+)\s*\[(.+)\]$/);
  if (m) {
    return {
      table: m[1],
      columns: splitTopLevel(m[2]),
    };
  }
  return { table: detail, columns: [] };
}

function parseJoinDetail(
  detail: string,
  name: string,
): { joinType: string; leftKey: string; rightKey: string; strategy: string } {
  const strategy = name
    .replace("Join", "")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .trim();
  const m = detail.match(
    /^(\w[\w\s]*?)\s+on\s+\[([^\]]*)\]\s*=\s*\[([^\]]*)\]$/,
  );
  if (m) {
    return {
      joinType: m[1].toUpperCase(),
      leftKey: m[2].trim(),
      rightKey: m[3].trim(),
      strategy,
    };
  }
  const simple = detail.match(/^(\w[\w\s]*?)\s+on\s+(.+)$/);
  if (simple) {
    return {
      joinType: simple[1].toUpperCase(),
      leftKey: simple[2].trim(),
      rightKey: "",
      strategy,
    };
  }
  return { joinType: detail.toUpperCase(), leftKey: "", rightKey: "", strategy };
}

function parseFilterPredicates(detail: string): string[] {
  // Strip outermost wrapping parens that don't contain content
  let s = detail.trim();
  while (s.startsWith("(") && s.endsWith(")") && isBalancedInner(s)) {
    s = s.slice(1, -1).trim();
  }

  // Split on AND/OR at the top level (depth 0), preserving parens on each side
  const parts: string[] = [];
  let depth = 0;
  let current = "";
  let i = 0;
  while (i < s.length) {
    const ch = s[i];
    if (ch === "(") depth++;
    else if (ch === ")") depth--;

    // Only split on ` AND ` or ` OR ` at depth 0 (don't consume surrounding parens)
    if (depth === 0) {
      const rest = s.slice(i);
      const match = rest.match(/^\s+(AND|OR)\s+/i);
      if (match) {
        current += ch; // include the current char first
        if (current.trim()) parts.push(cleanPredicate(current.trim()));
        current = "";
        i += match[0].length;
        continue;
      }
    }
    current += ch;
    i++;
  }
  if (current.trim()) parts.push(cleanPredicate(current));
  return parts.length > 0 ? parts : [detail];
}

function isBalancedInner(s: string): boolean {
  // Check if removing outer parens leaves a balanced string
  let depth = 0;
  for (let i = 1; i < s.length - 1; i++) {
    if (s[i] === "(") depth++;
    else if (s[i] === ")") depth--;
    if (depth < 0) return false;
  }
  return depth === 0;
}

function cleanPredicate(p: string): string {
  let s = p.trim();
  // Strip balanced outer parens
  while (s.startsWith("(") && s.endsWith(")") && isBalancedInner(s)) {
    s = s.slice(1, -1).trim();
  }
  return s;
}

/** Split on commas only at the top level (not inside parentheses). */
function splitTopLevel(s: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let current = "";
  for (const ch of s) {
    if (ch === "(") depth++;
    else if (ch === ")") depth--;
    if (ch === "," && depth <= 0) {
      parts.push(current.trim());
      current = "";
    } else {
      current += ch;
    }
  }
  if (current.trim()) parts.push(current.trim());
  return parts.filter(Boolean);
}

function parseProjectColumns(
  detail: string,
): { columns: string[]; expressions: string[] } {
  const items = splitTopLevel(detail);
  const columns: string[] = [];
  const expressions: string[] = [];
  for (const item of items) {
    if (item.includes("(")) {
      expressions.push(item);
    } else {
      columns.push(item);
    }
  }
  return { columns, expressions };
}

function parseAggregateDetail(
  detail: string,
): { groupBy: string[]; functions: string[] } {
  const parts = detail.split("|").map((s) => s.trim());
  let groupBy: string[] = [];
  let functions: string[] = [];
  if (parts.length >= 2) {
    const byStr = parts[0].replace(/^by\s+/i, "");
    groupBy = byStr
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    functions = parts[1]
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  } else if (detail.startsWith("by ")) {
    groupBy = detail
      .replace(/^by\s+/, "")
      .split(",")
      .map((s) => s.trim());
  } else {
    functions = detail
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return { groupBy, functions };
}

function parseSortKeys(
  detail: string,
): { column: string; direction: "ASC" | "DESC" }[] {
  return detail
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((part) => {
      if (part.includes("DESC"))
        return { column: part.replace(/\s*DESC.*/, ""), direction: "DESC" as const };
      return { column: part.replace(/\s*ASC.*/, ""), direction: "ASC" as const };
    });
}

// ── Metrics bar (shared across formatters) ──────────────────────

function MetricsBar({ metrics }: { metrics: Record<string, string> }) {
  const entries = Object.entries(metrics);
  if (entries.length === 0) return null;

  const timeEntry = entries.find(([k]) => TIME_KEYS.has(k));
  const rows = metrics.rows;
  const rest = entries.filter(
    ([k]) => k !== "rows" && !TIME_KEYS.has(k),
  );

  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-2.5 bg-black/20 rounded-xl border border-white/[0.04]">
      {timeEntry && (
        <span className="text-[11px] font-mono text-slate-300 flex items-center gap-1.5">
          <span className="text-slate-500">⏱</span>
          {timeEntry[1]}
        </span>
      )}
      {rows && (
        <span className="text-[11px] font-mono text-slate-300 flex items-center gap-1.5">
          <span className="text-slate-500">≣</span>
          {rows} rows
        </span>
      )}
      {rest.map(([key, val]) => (
        <span
          key={key}
          className="text-[11px] font-mono text-slate-400"
        >
          <span className="text-slate-600">{key}</span>{" "}
          {val}
        </span>
      ))}
    </div>
  );
}

// ── Formatted detail renderers ──────────────────────────────────

function ScanFormatted({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { table, columns } = parseScanDetail(detail);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <Table2 className="w-4 h-4 text-blue-400 shrink-0" />
        <span className="text-sm font-semibold text-blue-300 font-mono">
          {table}
        </span>
      </div>
      {columns.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2">
            Columns
            <span className="ml-1.5 text-slate-600">({columns.length})</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {columns.map((col) => (
              <span
                key={col}
                className="text-[11px] font-mono text-blue-300 bg-blue-500/10 border border-blue-500/20 rounded-md px-2 py-0.5"
              >
                {col}
              </span>
            ))}
          </div>
        </div>
      )}
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}

function JoinFormatted({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { joinType, leftKey, rightKey, strategy } = parseJoinDetail(
    detail,
    node.name,
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-300 bg-amber-500/15 border border-amber-500/25 rounded-lg px-2.5 py-1">
          {joinType}
        </span>
        {strategy && (
          <span className="text-[10px] font-mono text-slate-500">
            {strategy}
          </span>
        )}
      </div>
      {(leftKey || rightKey) && (
        <div className="flex items-center gap-3 px-4 py-3 bg-black/20 rounded-xl border border-white/[0.04]">
          <span className="text-xs font-mono text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-md px-2 py-0.5">
            {leftKey || "?"}
          </span>
          <ArrowRight className="w-4 h-4 text-slate-600 shrink-0" />
          <span className="text-xs font-mono text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-md px-2 py-0.5">
            {rightKey || leftKey || "?"}
          </span>
        </div>
      )}
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}

function FilterFormatted({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const predicates = parseFilterPredicates(detail);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <FilterIcon className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
        <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
          Predicates
          <span className="ml-1.5 text-slate-600">({predicates.length})</span>
        </span>
      </div>
      <div className="space-y-1.5">
        {predicates.map((pred, i) => (
          <div
            key={i}
            className="flex items-start gap-2 text-xs font-mono"
          >
            <span className="text-indigo-500/60 select-none shrink-0 w-4 text-right">
              {i + 1}
            </span>
            <span className="text-slate-300 leading-relaxed break-all">
              {pred.split(/(AND|OR|>=|<=|!=|<>|=|>|<|notnull|isnotnull)/gi).map((seg, j) => {
                const upper = seg.toUpperCase();
                if (upper === "AND" || upper === "OR") {
                  return (
                    <span key={j} className="text-amber-400 font-semibold">
                      {seg}
                    </span>
                  );
                }
                if ([">=", "<=", "!=", "<>", "=", ">", "<"].includes(seg)) {
                  return (
                    <span key={j} className="text-cyan-400">
                      {seg}
                    </span>
                  );
                }
                if (
                  seg.toLowerCase() === "notnull" ||
                  seg.toLowerCase() === "isnotnull"
                ) {
                  return (
                    <span key={j} className="text-violet-400">
                      {seg}
                    </span>
                  );
                }
                return <span key={j}>{seg}</span>;
              })}
            </span>
          </div>
        ))}
      </div>
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}

function ProjectFormatted({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { columns, expressions } = parseProjectColumns(detail);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Columns3 className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
        <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
          Output Columns
          <span className="ml-1.5 text-slate-600">
            ({columns.length + expressions.length})
          </span>
        </span>
      </div>
      {columns.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {columns.map((col) => (
            <span
              key={col}
              className="text-[11px] font-mono text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 rounded-md px-2 py-0.5"
            >
              {col}
            </span>
          ))}
        </div>
      )}
      {expressions.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-600 mb-1.5">
            Expressions
          </div>
          <div className="space-y-1">
            {expressions.map((expr, i) => (
              <div
                key={i}
                className="text-[11px] font-mono text-violet-300/80 bg-violet-500/5 border border-violet-500/10 rounded-md px-2.5 py-1 break-all"
              >
                {expr}
              </div>
            ))}
          </div>
        </div>
      )}
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}

function AggregateFormatted({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const { groupBy, functions } = parseAggregateDetail(detail);

  return (
    <div className="space-y-4">
      {groupBy.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2">
            Group By
          </div>
          <div className="flex flex-wrap gap-1.5">
            {groupBy.map((col) => (
              <span
                key={col}
                className="text-[11px] font-mono text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 rounded-md px-2 py-0.5"
              >
                {col}
              </span>
            ))}
          </div>
        </div>
      )}
      {functions.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-2">
            Aggregations
          </div>
          <div className="flex flex-wrap gap-1.5">
            {functions.map((fn) => (
              <span
                key={fn}
                className="text-[11px] font-mono text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-md px-2 py-0.5"
              >
                {fn}()
              </span>
            ))}
          </div>
        </div>
      )}
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}

function SortFormatted({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const keys = parseSortKeys(detail);

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        {keys.map((k, i) => (
          <div
            key={i}
            className="flex items-center gap-2 px-3 py-2 bg-black/20 rounded-lg border border-white/[0.04]"
          >
            {k.direction === "ASC" ? (
              <ChevronUp className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5 text-rose-400 shrink-0" />
            )}
            <span className="text-xs font-mono text-slate-300">{k.column}</span>
            <span className="text-[9px] font-mono text-slate-600 ml-auto">
              {k.direction}
            </span>
          </div>
        ))}
      </div>
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}

function ExchangeFormatted({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <Shuffle className="w-4 h-4 text-amber-400 shrink-0" />
        <span className="text-sm font-mono text-amber-300">{detail}</span>
      </div>
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}

function FallbackFormatted({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const entries = Object.entries(node.metrics);

  return (
    <div className="space-y-4">
      {detail && (
        <div className="text-xs font-mono text-slate-300 bg-black/30 p-3 rounded-lg break-all leading-relaxed whitespace-pre-wrap">
          {detail}
        </div>
      )}
      {entries.length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {entries.map(([key, val]) => (
            <div
              key={key}
              className="flex items-center justify-between bg-black/30 px-3 py-2 rounded-lg"
            >
              <span className="text-[10px] font-mono text-slate-500">
                {key}
              </span>
              <span className="text-xs font-mono text-slate-300">{val}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FormattedDetail({ node }: { node: ExecutionPlanNode }) {
  const lower = node.name.toLowerCase();
  if (lower.includes("scan") || lower.includes("datasource")) {
    return <ScanFormatted node={node} />;
  }
  if (lower.includes("join")) {
    return <JoinFormatted node={node} />;
  }
  if (lower === "filter") {
    return <FilterFormatted node={node} />;
  }
  if (lower === "project") {
    const detail = node.full_detail || node.detail;
    if (detail.includes("|")) return <AggregateFormatted node={node} />;
    return <ProjectFormatted node={node} />;
  }
  if (lower.includes("aggregate") || lower.includes("hashaggregate")) {
    return <AggregateFormatted node={node} />;
  }
  if (lower.includes("sort") && !lower.includes("merge")) {
    return <SortFormatted node={node} />;
  }
  if (lower.includes("exchange")) {
    return <ExchangeFormatted node={node} />;
  }
  return <FallbackFormatted node={node} />;
}

// ── Raw detail (original modal content) ─────────────────────────

function RawDetail({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const entries = Object.entries(node.metrics);

  return (
    <div className="space-y-4">
      {detail && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-1.5">
            Full Detail
          </div>
          <div className="text-xs font-mono text-slate-300 bg-black/30 p-3 rounded-lg break-all leading-relaxed whitespace-pre-wrap">
            {detail}
          </div>
        </div>
      )}
      {entries.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-1.5">
            Metrics
          </div>
          <div className="grid grid-cols-2 gap-2">
            {entries.map(([key, val]) => (
              <div
                key={key}
                className="flex items-center justify-between bg-black/30 px-3 py-2 rounded-lg"
              >
                <span className="text-[10px] font-mono text-slate-500">
                  {key}
                </span>
                <span className="text-xs font-mono text-slate-300">
                  {val}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Modal ────────────────────────────────────────────────────────

function NodeDetailModal({
  node,
  onClose,
}: {
  node: ExecutionPlanNode;
  onClose: () => void;
}) {
  const [activeTab, setActiveTab] = useState<"formatted" | "raw">("formatted");
  const style = NODE_STYLES[node.type] ?? NODE_STYLES.transform;
  const Icon = style.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-lg bg-[#141419] border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-xl border ${style.bg} ${style.border}`}
            >
              <Icon className={`w-4 h-4 ${style.text}`} />
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-semibold ${style.text}`}>
                {node.name}
              </span>
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 bg-white/5 px-1.5 py-0.5 rounded">
                {node.type}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab bar */}
        <div className="px-6 py-2 bg-black/20 border-b border-white/[0.04] flex gap-1">
          <button
            onClick={() => setActiveTab("formatted")}
            className={`px-3 py-1.5 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors ${
              activeTab === "formatted"
                ? "bg-white/10 text-white"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            Formatted
          </button>
          <button
            onClick={() => setActiveTab("raw")}
            className={`px-3 py-1.5 rounded-lg text-[11px] font-mono uppercase tracking-wider transition-colors ${
              activeTab === "raw"
                ? "bg-white/10 text-white"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            Raw
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 max-h-[60vh] overflow-y-auto">
          {activeTab === "formatted" ? (
            <FormattedDetail node={node} />
          ) : (
            <RawDetail node={node} />
          )}
        </div>
      </div>
    </div>
  );
}

function TreeNode({
  node,
  onExpand,
}: {
  node: ExecutionPlanNode;
  onExpand: (node: ExecutionPlanNode) => void;
}) {
  return (
    <li>
      <NodeCard node={node} onExpand={onExpand} />
      {node.children.length > 0 && (
        <ul>
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} onExpand={onExpand} />
          ))}
        </ul>
      )}
    </li>
  );
}

const treeStyles = `
.tree-container ul {
  padding-top: 30px;
  position: relative;
  display: flex;
  justify-content: center;
}
.tree-container li {
  float: left;
  text-align: center;
  list-style-type: none;
  position: relative;
  padding: 30px 15px 0 15px;
}
.tree-container li::before,
.tree-container li::after {
  content: '';
  position: absolute;
  top: 0;
  right: 50%;
  border-top: 2px solid #334155;
  width: 50%;
  height: 30px;
}
.tree-container li::after {
  right: auto;
  left: 50%;
  border-left: 2px solid #334155;
}
.tree-container li:only-child::after,
.tree-container li:only-child::before {
  display: none;
}
.tree-container li:only-child {
  padding-top: 0;
}
.tree-container li:first-child::before,
.tree-container li:last-child::after {
  border: 0 none;
}
.tree-container li:last-child::before {
  border-right: 2px solid #334155;
  border-radius: 0 8px 0 0;
}
.tree-container li:first-child::after {
  border-radius: 8px 0 0 0;
}
.tree-container ul ul::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  border-left: 2px solid #334155;
  width: 0;
  height: 30px;
  transform: translateX(-50%);
}
.tree-container > ul {
  padding-top: 0;
}
`;

function formatRunDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }) + " UTC";
}

function RunPicker({
  pipelineId,
  currentRunId,
  onSelect,
}: {
  pipelineId: string;
  currentRunId: string;
  onSelect: (dagRunId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useExecutionPlanRuns(pipelineId);

  const allRuns = data?.pages.flatMap((p) => p.items) ?? [];
  const total = data?.pages[0]?.total ?? 0;

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  // Infinite scroll: load more when scrolled near bottom
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !open) return;
    function onScroll() {
      if (!el || !hasNextPage || isFetchingNextPage) return;
      if (el.scrollTop + el.clientHeight >= el.scrollHeight - 40) {
        fetchNextPage();
      }
    }
    el.addEventListener("scroll", onScroll);
    return () => el.removeEventListener("scroll", onScroll);
  }, [open, hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (total <= 1) return null;

  const current = allRuns.find((r) => r.dag_run_id === currentRunId);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="text-[10px] font-mono px-2.5 py-1 rounded-full border transition-all cursor-pointer inline-flex items-center gap-1 text-indigo-300 bg-indigo-500/15 border-indigo-500/30"
      >
        {current ? formatRunDate(current.start_date) : "Latest"}
        <ChevronDown className={`w-2.5 h-2.5 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="absolute top-full right-0 mt-1 z-50 bg-[#18181b] border border-white/10 rounded-xl shadow-xl overflow-hidden min-w-[220px]">
          <div
            ref={scrollRef}
            className="max-h-[280px] overflow-y-auto custom-scrollbar"
          >
            {allRuns.map((run) => (
              <button
                key={run.dag_run_id}
                type="button"
                onClick={() => { onSelect(run.dag_run_id); setOpen(false); }}
                className={`w-full text-left px-3 py-2 text-[11px] font-mono transition-colors cursor-pointer flex items-center justify-between gap-3 ${
                  run.dag_run_id === currentRunId
                    ? "bg-indigo-500/10 text-indigo-300"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                }`}
              >
                <span>{formatRunDate(run.start_date)}</span>
                <span className="text-[9px] text-slate-600">{run.dag_id}</span>
              </button>
            ))}
            {isFetchingNextPage && (
              <div className="flex justify-center py-2">
                <Loader2 className="w-3.5 h-3.5 text-slate-600 animate-spin" />
              </div>
            )}
          </div>
          {total > 0 && (
            <div className="px-3 py-1.5 border-t border-white/5 text-[9px] font-mono text-slate-600 text-center">
              {allRuns.length} of {total} runs
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function TransformInspectorCard({
  pipelineId,
}: TransformInspectorCardProps) {
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>();
  const { data, isLoading } = useExecutionPlan(pipelineId, selectedRunId);
  const [expandedNode, setExpandedNode] = useState<ExecutionPlanNode | null>(
    null,
  );

  if (isLoading) {
    return (
      <div className="col-span-12 bg-[#18181b] border border-white/[0.06] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/[0.06] flex items-center gap-3">
          <Skeleton className="h-4 w-4 bg-white/5 rounded" />
          <Skeleton className="h-3 w-40 bg-white/5" />
        </div>
        <div className="p-10 flex justify-center">
          <Skeleton className="h-48 w-96 bg-white/5 rounded-xl" />
        </div>
      </div>
    );
  }

  if (!data?.execution_plan) return null;

  return (
    <div className="col-span-12 bg-[#18181b] border border-white/[0.06] rounded-2xl overflow-hidden">
      <style>{treeStyles}</style>

      {/* Header */}
      <div className="px-6 py-4 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <GitMerge className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-mono uppercase tracking-widest text-slate-300">
            Logical Execution DAG
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-3 text-[11px] font-mono text-slate-500">
            <span>{data.dag_id}</span>
            {data.duration_seconds != null && (
              <>
                <span className="text-slate-700">|</span>
                <span>{formatDuration(data.duration_seconds)}</span>
              </>
            )}
          </div>
          <RunPicker
            pipelineId={pipelineId}
            currentRunId={data.dag_run_id}
            onSelect={setSelectedRunId}
          />
        </div>
      </div>

      {/* Canvas body */}
      <div className="relative overflow-x-auto" style={{ maxHeight: 500 }}>
        <div
          className="absolute inset-0 opacity-[0.08] pointer-events-none"
          style={{
            backgroundImage:
              "radial-gradient(#94a3b8 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
        />
        <div className="relative min-w-max flex justify-center p-10">
          <div className="tree-container">
            <ul>
              <TreeNode
                node={data.execution_plan}
                onExpand={setExpandedNode}
              />
            </ul>
          </div>
        </div>
      </div>

      {/* Node detail modal */}
      {expandedNode && (
        <NodeDetailModal
          node={expandedNode}
          onClose={() => setExpandedNode(null)}
        />
      )}
    </div>
  );
}
