import { Filter as FilterIcon } from "lucide-react";
import { parseFilterPredicates, simplifyPredicate, formatSQL } from "../plan-parsers";
import { MetricsBar } from "./MetricsBar";
import type { ExecutionPlanNode } from "@/types/execution-plan";

function highlightSQL(text: string) {
  // Split on keywords, operators, and null checks — then style each segment
  const parts = text.split(
    /(AND|OR|NOT|IN|LIKE|BETWEEN|IS|CASE|WHEN|THEN|ELSE|END|TRUE|FALSE|ASC|DESC|EXISTS|ANY|ALL|>=|<=|!=|<>|=|>|<|(?:IS\s+)?(?:NOT\s+)?NULL|NOTNULL|ISNOTNULL)/gi,
  );

  return parts.map((seg, j) => {
    const upper = seg.toUpperCase().trim();
    if (["AND", "OR"].includes(upper)) {
      return (
        <span key={j} className="text-amber-400 font-semibold">
          {seg}
        </span>
      );
    }
    if (
      [
        "CASE", "WHEN", "THEN", "ELSE", "END",
        "IN", "LIKE", "BETWEEN", "NOT",
        "EXISTS", "ANY", "ALL", "IS",
        "TRUE", "FALSE", "ASC", "DESC",
      ].includes(upper)
    ) {
      return (
        <span key={j} className="text-violet-400">
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
    if (/^(IS\s+)?(NOT\s+)?NULL$|^NOTNULL$|^ISNOTNULL$/i.test(upper)) {
      return (
        <span key={j} className="text-violet-400">
          {seg}
        </span>
      );
    }
    return <span key={j}>{seg}</span>;
  });
}

function SimplifiedDisplay({
  column,
  values,
}: {
  column: string;
  values: string[];
}) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-slate-300 font-mono text-xs shrink-0">
        {column}{" "}
        <span className="text-violet-400">IN</span>
      </span>
      <div className="flex flex-wrap gap-1">
        {values.map((v, i) => (
          <span
            key={i}
            className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
          >
            {v}
          </span>
        ))}
      </div>
    </div>
  );
}

function FormattedSQLDisplay({ predicate }: { predicate: string }) {
  const lines = formatSQL(predicate);

  if (lines.length === 1) {
    // Single line — inline highlight
    return (
      <span className="text-slate-300 leading-relaxed break-all">
        {highlightSQL(lines[0])}
      </span>
    );
  }

  // Multi-line formatted SQL
  return (
    <div className="font-mono text-xs space-y-0.5">
      {lines.map((line, i) => (
        <div key={i} className="text-slate-300" style={{ whiteSpace: "pre" }}>
          {highlightSQL(line)}
        </div>
      ))}
    </div>
  );
}

export function FilterFormatter({ node }: { node: ExecutionPlanNode }) {
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
      <div className="space-y-2.5">
        {predicates.map((pred, i) => {
          const result = simplifyPredicate(pred);

          return (
            <div
              key={i}
              className="flex items-start gap-2 text-xs font-mono"
            >
              <span className="text-indigo-500/60 select-none shrink-0 w-4 text-right mt-0.5">
                {i + 1}
              </span>
              <div className="min-w-0">
                {result.simplified ? (
                  <SimplifiedDisplay
                    column={result.column}
                    values={result.values}
                  />
                ) : (
                  <FormattedSQLDisplay predicate={pred} />
                )}
              </div>
            </div>
          );
        })}
      </div>
      <MetricsBar metrics={node.metrics} />
    </div>
  );
}
