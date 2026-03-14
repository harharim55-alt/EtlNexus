import { useState } from "react";
import {
  X,
  ArrowRight,
  ChevronUp,
  ChevronDown,
  Columns3,
  Filter as FilterIcon,
  Shuffle,
  Table2,
} from "lucide-react";
import { NODE_STYLES, TIME_KEYS } from "./plan-constants";
import {
  parseScanDetail,
  parseJoinDetail,
  parseFilterPredicates,
  parseProjectColumns,
  parseAggregateDetail,
  parseSortKeys,
} from "./plan-parsers";
import type { ExecutionPlanNode } from "@/types/execution-plan";

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

export function NodeDetailModal({
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
