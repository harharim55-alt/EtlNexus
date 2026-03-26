// ── Detail parsing helpers ───────────────────────────────────────

export function parseScanDetail(detail: string): {
  table: string;
  namespace: string;
  columns: string[];
  filters: string[];
} {
  // Full detail may be multi-line:
  //   TableName [col1, col2, ...]
  //   namespace: vault
  //   filters: date IS NOT NULL, date >= 20535
  const lines = detail.split("\n").map((l) => l.trim());

  let table = "";
  let namespace = "";
  let columns: string[] = [];
  let filters: string[] = [];

  // First line: table [columns]
  const first = lines[0] || detail;
  const m = first.match(/^(\S+)\s*\[(.+)\]$/);
  if (m) {
    table = m[1];
    columns = splitTopLevel(m[2]);
  } else {
    table = first;
  }

  for (const line of lines.slice(1)) {
    if (line.startsWith("namespace:")) {
      namespace = line.replace("namespace:", "").trim();
    } else if (line.startsWith("filters:")) {
      const raw = line.replace("filters:", "").trim();
      if (raw) {
        // Use splitTopLevel to avoid splitting inside IN (...) clauses
        filters = splitTopLevel(raw);
      }
    }
  }

  return { table, namespace, columns, filters };
}

export function parseJoinDetail(
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

export function parseFilterPredicates(detail: string): string[] {
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

export function isBalancedInner(s: string): boolean {
  // Check if removing outer parens leaves a balanced string
  let depth = 0;
  for (let i = 1; i < s.length - 1; i++) {
    if (s[i] === "(") depth++;
    else if (s[i] === ")") depth--;
    if (depth < 0) return false;
  }
  return depth === 0;
}

export function cleanPredicate(p: string): string {
  let s = p.trim();
  // Strip balanced outer parens
  while (s.startsWith("(") && s.endsWith(")") && isBalancedInner(s)) {
    s = s.slice(1, -1).trim();
  }
  return s;
}

/** Split on commas only at the top level (not inside parentheses). */
export function splitTopLevel(s: string): string[] {
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

export function parseProjectColumns(
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

export function parseAggregateDetail(
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

export function parseSortKeys(
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

// ── Smart predicate simplification ──────────────────────────────

export interface SimplifiedPredicate {
  simplified: true;
  column: string;
  values: string[];
}

export interface UnsimplifiedPredicate {
  simplified: false;
}

export type PredicateSimplification = SimplifiedPredicate | UnsimplifiedPredicate;

/**
 * Detect patterns that can be collapsed into `column IN (v1, v2, ...)`:
 *  - CASE WHEN (col = v1) THEN true WHEN (col = v2) THEN true ... ELSE false END
 *  - (col = v1) OR (col = v2) OR ...
 */
export function simplifyPredicate(pred: string): PredicateSimplification {
  const s = pred.trim();

  // Pattern 1: CASE WHEN (col = v) THEN true ... ELSE false END
  const caseMatch = s.match(/^CASE\s+(.+?)\s+ELSE\s+false\s+END$/i);
  if (caseMatch) {
    const whenBody = caseMatch[1];
    const whenParts = [...whenBody.matchAll(/WHEN\s+\(?(\w+)\s*=\s*(\w+)\)?\s+THEN\s+true/gi)];
    if (whenParts.length >= 2) {
      const columns = new Set(whenParts.map((m) => m[1]));
      if (columns.size === 1) {
        return {
          simplified: true,
          column: whenParts[0][1],
          values: whenParts.map((m) => m[2]),
        };
      }
    }
  }

  // Pattern 2: (col = v1) OR (col = v2) OR ...
  const orParts = s.split(/\s+OR\s+/i).map((p) => p.trim());
  if (orParts.length >= 2) {
    const eqMatches = orParts.map((p) => {
      const cleaned = p.replace(/^\(/, "").replace(/\)$/, "").trim();
      return cleaned.match(/^(\w+)\s*=\s*(\w+)$/);
    });
    if (eqMatches.every((m) => m !== null)) {
      const columns = new Set(eqMatches.map((m) => m![1]));
      if (columns.size === 1) {
        return {
          simplified: true,
          column: eqMatches[0]![1],
          values: eqMatches.map((m) => m![2]),
        };
      }
    }
  }

  return { simplified: false };
}

/**
 * Format a complex SQL expression with indentation for readability.
 * Puts each WHEN on its own line, indented under CASE.
 */
export function formatSQL(pred: string): string[] {
  const s = pred.trim();

  // If it contains CASE, format with indentation
  if (/\bCASE\b/i.test(s)) {
    const lines: string[] = [];
    // Split on WHEN/ELSE/END boundaries
    let remaining = s;

    const caseIdx = remaining.search(/\bCASE\b/i);
    if (caseIdx >= 0) {
      const before = remaining.slice(0, caseIdx).trim();
      if (before) lines.push(before);
      remaining = remaining.slice(caseIdx);
    }

    // Extract CASE keyword
    lines.push("CASE");
    remaining = remaining.replace(/^\s*CASE\s*/i, "");

    // Extract WHEN ... THEN ... clauses
    const whenRegex = /\bWHEN\b\s+(.+?)\s+\bTHEN\b\s+(\S+)/gi;
    let match;
    while ((match = whenRegex.exec(remaining)) !== null) {
      lines.push(`  WHEN ${match[1].trim()} THEN ${match[2]}`);
    }

    // Extract ELSE
    const elseMatch = remaining.match(/\bELSE\b\s+(\S+)/i);
    if (elseMatch) {
      lines.push(`  ELSE ${elseMatch[1]}`);
    }

    lines.push("END");
    return lines;
  }

  // No CASE — return as-is
  return [s];
}

export function parseWindowDetail(detail: string): {
  partitionBy: string[];
  orderBy: { column: string; direction: "ASC" | "DESC" }[];
  functions: string[];
} {
  // Detail format from backend: "partition by col1, col2 | order by col3 DESC | func1, func2"
  const sections = detail.split("|").map((s) => s.trim());

  let partitionBy: string[] = [];
  let orderBy: { column: string; direction: "ASC" | "DESC" }[] = [];
  let functions: string[] = [];

  for (const section of sections) {
    if (section.startsWith("partition by ")) {
      partitionBy = section
        .replace(/^partition by\s+/, "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    } else if (section.startsWith("order by ")) {
      const raw = section.replace(/^order by\s+/, "");
      orderBy = raw
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((part) => {
          if (part.includes("DESC"))
            return { column: part.replace(/\s*DESC.*/, ""), direction: "DESC" as const };
          return { column: part.replace(/\s*ASC.*/, ""), direction: "ASC" as const };
        });
    } else if (section) {
      functions = section
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    }
  }

  return { partitionBy, orderBy, functions };
}
