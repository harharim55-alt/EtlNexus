// ── Detail parsing helpers ───────────────────────────────────────

export function parseScanDetail(detail: string): {
  table: string;
  namespace: string;
  columns: string[];
  filters: string[];
  format: string;
  location: string;
} {
  // Full detail may be multi-line:
  //   TableName [col1, col2, ...]
  //   namespace: vault
  //   format: parquet
  //   location: s3a://bucket/path
  //   filters: date IS NOT NULL, date >= 20535
  const lines = detail.split("\n").map((l) => l.trim());

  let table = "";
  let namespace = "";
  let columns: string[] = [];
  let filters: string[] = [];
  let format = "";
  let location = "";

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
    } else if (line.startsWith("format:")) {
      format = line.replace("format:", "").trim();
    } else if (line.startsWith("location:")) {
      location = line.replace("location:", "").trim();
    } else if (line.startsWith("filters:")) {
      const raw = line.replace("filters:", "").trim();
      if (raw) {
        // Use splitTopLevel to avoid splitting inside IN (...) clauses
        filters = splitTopLevel(raw);
      }
    }
  }

  return { table, namespace, columns, filters, format, location };
}

export function parseJoinDetail(
  detail: string,
  name: string,
): {
  joinType: string;
  leftKey: string;
  rightKey: string;
  strategy: string;
  buildSide: string;
  condition: string;
} {
  // Parse pipe-separated sections from full_detail:
  // "inner on [key] = [key] | strategy: Broadcast Hash | build: left"
  const sections = detail.split("|").map((s) => s.trim());
  const mainPart = sections[0] || "";
  let strategy = "";
  let buildSide = "";
  let condition = "";

  for (const section of sections.slice(1)) {
    if (section.startsWith("strategy:")) {
      strategy = section.replace("strategy:", "").trim();
    } else if (section.startsWith("build:")) {
      buildSide = section.replace("build:", "").trim();
    } else if (section.startsWith("condition:")) {
      condition = section.replace("condition:", "").trim();
    } else if (!section.startsWith("strategy") && !section.startsWith("build")) {
      // Legacy: strategy was in short detail after pipe
      strategy = section;
    }
  }

  // Fallback strategy from node name if not in detail
  if (!strategy) {
    strategy = name
      .replace("Join", "")
      .replace("CartesianProduct", "Cartesian")
      .replace(/([a-z])([A-Z])/g, "$1 $2")
      .trim();
  }

  const m = mainPart.match(
    /^(\w[\w\s]*?)\s+on\s+\[([^\]]*)\]\s*=\s*\[([^\]]*)\]$/,
  );
  if (m) {
    return {
      joinType: m[1].toUpperCase(),
      leftKey: m[2].trim(),
      rightKey: m[3].trim(),
      strategy,
      buildSide,
      condition,
    };
  }
  const simple = mainPart.match(/^(\w[\w\s]*?)\s+on\s+(.+)$/);
  if (simple) {
    return {
      joinType: simple[1].toUpperCase(),
      leftKey: simple[2].trim(),
      rightKey: "",
      strategy,
      buildSide,
      condition,
    };
  }
  return {
    joinType: mainPart.toUpperCase() || "JOIN",
    leftKey: "",
    rightKey: "",
    strategy,
    buildSide,
    condition,
  };
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

export function parseProjectColumns(detail: string): {
  columns: string[];
  expressions: string[];
  passthrough: string[];
  renamed: { from: string; to: string }[];
  computed: { expression: string; alias: string }[];
} {
  // Try structured format: "passthrough: ...\nrenamed: ...\ncomputed: ..."
  const lines = detail.split("\n").map((l) => l.trim());
  const passthrough: string[] = [];
  const renamed: { from: string; to: string }[] = [];
  const computed: { expression: string; alias: string }[] = [];
  let hasStructured = false;

  for (const line of lines) {
    if (line.startsWith("passthrough:")) {
      hasStructured = true;
      passthrough.push(
        ...line
          .replace("passthrough:", "")
          .trim()
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      );
    } else if (line.startsWith("renamed:")) {
      hasStructured = true;
      const items = splitTopLevel(line.replace("renamed:", "").trim());
      for (const item of items) {
        const m = item.match(/^(.+?)\s+AS\s+(.+)$/);
        if (m) {
          renamed.push({ from: m[1].trim(), to: m[2].trim() });
        }
      }
    } else if (line.startsWith("computed:")) {
      hasStructured = true;
      const items = splitTopLevel(line.replace("computed:", "").trim());
      for (const item of items) {
        const m = item.match(/^(.+?)\s+AS\s+(\S+)$/);
        if (m) {
          computed.push({ expression: m[1].trim(), alias: m[2].trim() });
        } else {
          computed.push({ expression: item, alias: "" });
        }
      }
    }
  }

  if (hasStructured) {
    // Build legacy columns/expressions for backward compat
    const columns = [...passthrough, ...renamed.map((r) => r.to)];
    const expressions = computed.map((c) =>
      c.alias ? `${c.expression} AS ${c.alias}` : c.expression,
    );
    return { columns, expressions, passthrough, renamed, computed };
  }

  // Fallback: old comma-separated format
  const items = splitTopLevel(detail);
  const oldColumns: string[] = [];
  const oldExpressions: string[] = [];
  for (const item of items) {
    if (item.includes("(")) {
      oldExpressions.push(item);
    } else {
      oldColumns.push(item);
    }
  }
  return {
    columns: oldColumns,
    expressions: oldExpressions,
    passthrough: oldColumns,
    renamed: [],
    computed: oldExpressions.map((e) => ({ expression: e, alias: "" })),
  };
}

export function parseAggregateDetail(
  detail: string,
): { groupBy: string[]; functions: string[]; phase: string } {
  const parts = detail.split("|").map((s) => s.trim());
  let groupBy: string[] = [];
  let functions: string[] = [];
  let phase = "";

  // Check for phase prefix: "partial | by col | sum" or "phase: partial | by col | sum"
  const filtered: string[] = [];
  for (const part of parts) {
    if (part === "partial" || part === "final") {
      phase = part;
    } else if (part.startsWith("phase:")) {
      phase = part.replace("phase:", "").trim();
    } else {
      filtered.push(part);
    }
  }

  if (filtered.length >= 2) {
    const byStr = filtered[0].replace(/^by\s+/i, "");
    groupBy = byStr
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    functions = filtered[1]
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  } else if (filtered.length === 1) {
    const single = filtered[0];
    if (single.startsWith("by ")) {
      groupBy = single
        .replace(/^by\s+/, "")
        .split(",")
        .map((s) => s.trim());
    } else {
      functions = single
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    }
  }
  return { groupBy, functions, phase };
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

// ── Smart filter parsing ────────────────────────────────────────

export interface SmartFilter {
  dateRanges: { column: string; from: string; to: string }[];
  notNulls: string[];
  equalities: { column: string; value: string }[];
  inLists: { column: string; values: string[] }[];
  booleans: string[];
  ranges: { column: string; op: string; value: string }[];
  complex: string[];
}

/**
 * Recursively flatten a compound predicate into atomic conditions.
 * Strips outer parens and splits on AND/OR, then recurses on any
 * part that still contains AND/OR at depth 0.
 */
function flattenPredicates(detail: string): string[] {
  let s = detail.trim();
  // Strip outer balanced parens
  while (s.startsWith("(") && s.endsWith(")") && isBalancedInner(s)) {
    s = s.slice(1, -1).trim();
  }

  // Split on AND at depth 0
  const parts = parseFilterPredicates(s);
  const result: string[] = [];
  for (const part of parts) {
    let p = part.trim();
    // Strip outer parens again on each part
    while (p.startsWith("(") && p.endsWith(")") && isBalancedInner(p)) {
      p = p.slice(1, -1).trim();
    }
    // If it still contains AND at depth 0, recurse
    const subParts = parseFilterPredicates(p);
    if (subParts.length > 1) {
      result.push(...flattenPredicates(p));
    } else {
      result.push(p);
    }
  }
  return result;
}

/**
 * Classify a single atomic predicate into a smart filter category.
 * Returns true if classified, false if it should go to complex.
 */
function classifyPredicate(
  trimmed: string,
  result: SmartFilter,
  rangeParts: Map<string, { op: string; value: string }[]>,
): boolean {
  // CASE→IN simplification
  const sub = simplifyPredicate(trimmed);
  if (sub.simplified) {
    result.inLists.push({ column: sub.column, values: sub.values });
    return true;
  }

  // NOT NULL: notnull(col) or isnotnull(col)
  const nnMatch = trimmed.match(/^(?:is)?notnull\((\w+)\)$/i);
  if (nnMatch) {
    result.notNulls.push(nnMatch[1]);
    return true;
  }

  // Filter isnotnull(col) — with "Filter" prefix from detail
  const nnMatch2 = trimmed.match(/^Filter\s+isnotnull\((\w+)\)$/i);
  if (nnMatch2) {
    result.notNulls.push(nnMatch2[1]);
    return true;
  }

  // IN list: col IN (v1,v2,v3)
  const inMatch = trimmed.match(/^(\w+)\s+IN\s+\((.+)\)$/i);
  if (inMatch) {
    const values = inMatch[2].split(",").map((v) => v.trim()).filter(Boolean);
    result.inLists.push({ column: inMatch[1], values });
    return true;
  }

  // Equality: (col = value) or col = value
  const eqMatch = trimmed.match(/^\(?(\w+)\s*=\s*(\S+?)\)?$/);
  if (eqMatch) {
    result.equalities.push({ column: eqMatch[1], value: eqMatch[2] });
    return true;
  }

  // Range comparisons: (col >= value), (col < value), etc.
  const rangeMatch = trimmed.match(/^\(?(\w+)\s*(>=|<=|>|<)\s*(\S+?)\)?$/);
  if (rangeMatch) {
    const col = rangeMatch[1];
    if (!rangeParts.has(col)) rangeParts.set(col, []);
    rangeParts.get(col)!.push({ op: rangeMatch[2], value: rangeMatch[3] });
    return true;
  }

  // Boolean: bare column name (e.g., is_active)
  if (/^\w+$/.test(trimmed)) {
    result.booleans.push(trimmed);
    return true;
  }

  return false;
}

/**
 * Parse a compound filter predicate into semantic groups.
 * Recursively flattens nested AND expressions, then classifies each.
 */
export function parseSmartFilter(detail: string): SmartFilter {
  const result: SmartFilter = {
    dateRanges: [],
    notNulls: [],
    equalities: [],
    inLists: [],
    booleans: [],
    ranges: [],
    complex: [],
  };

  // First, try CASE→IN simplification on the whole expression
  const caseResult = simplifyPredicate(detail);
  if (caseResult.simplified) {
    result.inLists.push({ column: caseResult.column, values: caseResult.values });
    return result;
  }

  // Recursively flatten into atomic predicates
  const atoms = flattenPredicates(detail);

  // Temporary storage for range merging
  const rangeParts: Map<string, { op: string; value: string }[]> = new Map();

  for (const atom of atoms) {
    if (!classifyPredicate(atom, result, rangeParts)) {
      result.complex.push(atom);
    }
  }

  // Merge range parts into date ranges or individual ranges
  for (const [col, parts] of rangeParts) {
    const gte = parts.find((p) => p.op === ">=" || p.op === ">");
    const lt = parts.find((p) => p.op === "<" || p.op === "<=");
    if (gte && lt) {
      result.dateRanges.push({ column: col, from: gte.value, to: lt.value });
    } else {
      for (const p of parts) {
        result.ranges.push({ column: col, op: p.op, value: p.value });
      }
    }
  }

  return result;
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

// ── Phase 1A: Set Operations, Dedup, Sample ──────────────────────

export function parseSetOpDetail(
  detail: string,
  name: string,
): { operation: string; isAll: boolean } {
  const lower = name.toLowerCase();
  const operation = lower.includes("except") ? "EXCEPT" : "INTERSECT";
  const isAll = detail.includes("all") || lower.includes("all");
  return { operation, isAll };
}

export function parseDeduplicateDetail(detail: string): { columns: string[] } {
  const columns = detail
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  return { columns };
}

export function parseSampleDetail(detail: string): {
  fraction: string;
  withReplacement: boolean;
  seed: string | null;
} {
  // Short detail: "50% | with replacement | seed=42"
  // Full detail: "fraction: 50%\nwith replacement: yes\nseed: 42"
  const lines = detail.split("\n").map((l) => l.trim());

  // Try structured format first
  let fraction = "";
  let withReplacement = false;
  let seed: string | null = null;

  for (const line of lines) {
    if (line.startsWith("fraction:")) {
      fraction = line.replace("fraction:", "").trim();
    } else if (line.startsWith("with replacement:")) {
      withReplacement = line.includes("yes");
    } else if (line.startsWith("seed:")) {
      seed = line.replace("seed:", "").trim();
    }
  }

  // Fallback to pipe-separated short format
  if (!fraction) {
    const parts = detail.split("|").map((s) => s.trim());
    fraction = parts[0] || "";
    withReplacement = parts.some((p) => p.includes("replacement"));
    const seedPart = parts.find((p) => p.startsWith("seed="));
    seed = seedPart ? seedPart.replace("seed=", "") : null;
  }

  return { fraction, withReplacement, seed };
}

// ── Phase 1B: Data Source Nodes ──────────────────────────────────

export function parseRangeDetail(detail: string): {
  start: string;
  end: string;
  step: string;
  partitions: string;
} {
  // Full detail: "start: 0\nend: 1000000\nstep: 1\npartitions: 8"
  const lines = detail.split("\n").map((l) => l.trim());

  let start = "";
  let end = "";
  let step = "";
  let partitions = "";

  for (const line of lines) {
    if (line.startsWith("start:")) start = line.replace("start:", "").trim();
    else if (line.startsWith("end:")) end = line.replace("end:", "").trim();
    else if (line.startsWith("step:")) step = line.replace("step:", "").trim();
    else if (line.startsWith("partitions:"))
      partitions = line.replace("partitions:", "").trim();
  }

  // Fallback to short format: "0 to 1,000,000 (step 1) | 8 parts"
  if (!start) {
    const m = detail.match(/^(.+?)\s+to\s+(.+?)(?:\s+\(step\s+(.+?)\))?/);
    if (m) {
      start = m[1];
      end = m[2];
      step = m[3] || "1";
    }
    const pm = detail.match(/(\d+)\s+parts/);
    if (pm) partitions = pm[1];
  }

  return { start, end, step, partitions };
}
