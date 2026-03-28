import { CalendarDays, Filter as FilterIcon, KeyRound, ListChecks, ToggleRight } from "lucide-react";
import { parseSmartFilter, formatSQL, type SmartFilter } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

/* ── SQL keyword highlighting ──────────────────────────────────── */

function highlightSQL(text: string) {
  const parts = text.split(
    /(AND|OR|NOT|IN|LIKE|BETWEEN|IS|CASE|WHEN|THEN|ELSE|END|TRUE|FALSE|ASC|DESC|EXISTS|ANY|ALL|>=|<=|!=|<>|=|>|<|(?:IS\s+)?(?:NOT\s+)?NULL|NOTNULL|ISNOTNULL)/gi,
  );
  return parts.map((seg, j) => {
    const upper = seg.toUpperCase().trim();
    if (["AND", "OR"].includes(upper))
      return <span key={j} className="text-amber-400 font-semibold">{seg}</span>;
    if ([
      "CASE", "WHEN", "THEN", "ELSE", "END", "IN", "LIKE",
      "BETWEEN", "NOT", "EXISTS", "ANY", "ALL", "IS",
      "TRUE", "FALSE", "ASC", "DESC",
    ].includes(upper))
      return <span key={j} className="text-violet-400">{seg}</span>;
    if ([">=", "<=", "!=", "<>", "=", ">", "<"].includes(seg))
      return <span key={j} className="text-cyan-400">{seg}</span>;
    if (/^(IS\s+)?(NOT\s+)?NULL$|^NOTNULL$|^ISNOTNULL$/i.test(upper))
      return <span key={j} className="text-violet-400">{seg}</span>;
    return <span key={j}>{seg}</span>;
  });
}

/* ── Shared styles ─────────────────────────────────────────────── */

const groupCard =
  "bg-hover-bg border border-border rounded-lg px-3 py-2.5";
const groupLabel =
  "text-[9px] font-mono uppercase tracking-widest text-text-faint flex items-center gap-1.5 mb-2";
const valuePill =
  "text-[11px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20";
const mutedPill =
  "text-[11px] font-mono px-1.5 py-0.5 rounded bg-hover-bg text-text-muted border border-border";

/* ── Group renderers ───────────────────────────────────────────── */

function DateRangeGroup({ ranges }: { ranges: SmartFilter["dateRanges"] }) {
  if (!ranges.length) return null;

  function formatDateVal(v: string) {
    // Try to parse YYYY-MM-DD into a short date
    const m = v.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (m) {
      const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
      return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    }
    return v;
  }

  return (
    <div className={groupCard}>
      <div className={groupLabel}>
        <CalendarDays className="w-3 h-3" />
        Date Range
      </div>
      <div className="space-y-1">
        {ranges.map((r, i) => (
          <div key={i} className="flex items-center gap-2 text-xs font-mono">
            <span className="text-text-secondary">{r.column}</span>
            <span className="text-emerald-400">{formatDateVal(r.from)}</span>
            <span className="text-text-faint">→</span>
            <span className="text-emerald-400">{formatDateVal(r.to)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function InListGroup({ lists }: { lists: SmartFilter["inLists"] }) {
  if (!lists.length) return null;
  return (
    <div className={groupCard}>
      <div className={groupLabel}>
        <ListChecks className="w-3 h-3" />
        Value Filters
      </div>
      <div className="space-y-2">
        {lists.map((item, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className="text-xs font-mono text-text-primary shrink-0 mt-0.5">
              {item.column}{" "}
              <span className="text-violet-400">IN</span>
            </span>
            <div className="flex flex-wrap gap-1">
              {item.values.map((v, j) => (
                <span key={j} className={valuePill}>{v}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EqualityGroup({
  equalities,
  booleans,
}: {
  equalities: SmartFilter["equalities"];
  booleans: SmartFilter["booleans"];
}) {
  if (!equalities.length && !booleans.length) return null;
  return (
    <div className={groupCard}>
      <div className={groupLabel}>
        <KeyRound className="w-3 h-3" />
        Conditions
      </div>
      <div className="flex flex-wrap gap-1.5">
        {equalities.map((eq, i) => (
          <span key={`eq-${i}`} className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
            {eq.column} <span className="text-cyan-400">=</span> {eq.value}
          </span>
        ))}
        {booleans.map((b, i) => (
          <span key={`bool-${i}`} className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 flex items-center gap-1">
            <ToggleRight className="w-3 h-3" />
            {b}
          </span>
        ))}
      </div>
    </div>
  );
}

function RangeGroup({ ranges }: { ranges: SmartFilter["ranges"] }) {
  if (!ranges.length) return null;
  return (
    <div className={groupCard}>
      <div className={groupLabel}>
        <FilterIcon className="w-3 h-3" />
        Ranges
      </div>
      <div className="flex flex-wrap gap-1.5">
        {ranges.map((r, i) => (
          <span key={i} className="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
            {r.column} <span className="text-cyan-400">{r.op}</span> {r.value}
          </span>
        ))}
      </div>
    </div>
  );
}

function NotNullGroup({ columns }: { columns: string[] }) {
  if (!columns.length) return null;
  return (
    <div className={groupCard}>
      <div className={groupLabel}>
        Required Fields
        <span className="text-text-faint">({columns.length})</span>
      </div>
      <div className="flex flex-wrap gap-1">
        {columns.map((col, i) => (
          <span key={i} className={mutedPill}>{col}</span>
        ))}
      </div>
    </div>
  );
}

function ComplexGroup({ predicates }: { predicates: string[] }) {
  if (!predicates.length) return null;
  return (
    <div className={groupCard}>
      <div className={groupLabel}>
        <FilterIcon className="w-3 h-3" />
        Expressions
      </div>
      <div className="space-y-2">
        {predicates.map((pred, i) => {
          const lines = formatSQL(pred);
          return (
            <div key={i} className="font-mono text-xs">
              {lines.length === 1 ? (
                <span className="text-text-primary break-all">{highlightSQL(lines[0])}</span>
              ) : (
                <div className="space-y-0.5">
                  {lines.map((line, j) => (
                    <div key={j} className="text-text-primary" style={{ whiteSpace: "pre" }}>
                      {highlightSQL(line)}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Main formatter ────────────────────────────────────────────── */

export function FilterFormatter({ node }: { node: ExecutionPlanNode }) {
  const detail = node.full_detail || node.detail;
  const smart = parseSmartFilter(detail);

  const totalConditions =
    smart.dateRanges.length +
    smart.notNulls.length +
    smart.equalities.length +
    smart.inLists.length +
    smart.booleans.length +
    smart.ranges.length +
    smart.complex.length;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <FilterIcon className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
        <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted">
          Filter
          <span className="ml-1.5 text-text-faint">
            ({totalConditions} condition{totalConditions !== 1 ? "s" : ""})
          </span>
        </span>
      </div>

      <DateRangeGroup ranges={smart.dateRanges} />
      <InListGroup lists={smart.inLists} />
      <EqualityGroup equalities={smart.equalities} booleans={smart.booleans} />
      <RangeGroup ranges={smart.ranges} />
      <ComplexGroup predicates={smart.complex} />
      <NotNullGroup columns={smart.notNulls} />

      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
