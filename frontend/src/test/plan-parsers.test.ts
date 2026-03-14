import { describe, it, expect } from "vitest";
import {
  parseScanDetail,
  parseJoinDetail,
  parseFilterPredicates,
  parseSortKeys,
  parseProjectColumns,
  parseAggregateDetail,
} from "@/components/bento-workspace/execution-plan/plan-parsers";

describe("parseScanDetail", () => {
  it("extracts table and columns from bracket notation", () => {
    const result = parseScanDetail("my_table [col_a, col_b, col_c]");
    expect(result.table).toBe("my_table");
    expect(result.columns).toEqual(["col_a", "col_b", "col_c"]);
  });

  it("returns full detail as table when no brackets", () => {
    const result = parseScanDetail("just_a_table");
    expect(result.table).toBe("just_a_table");
    expect(result.columns).toEqual([]);
  });
});

describe("parseJoinDetail", () => {
  it("extracts join type and keys from bracket notation", () => {
    const result = parseJoinDetail(
      "Inner on [left_key] = [right_key]",
      "SortMergeJoin",
    );
    expect(result.joinType).toBe("INNER");
    expect(result.leftKey).toBe("left_key");
    expect(result.rightKey).toBe("right_key");
    expect(result.strategy).toBe("Sort Merge");
  });

  it("handles simple on clause without brackets", () => {
    const result = parseJoinDetail(
      "Left on some_condition",
      "BroadcastHashJoin",
    );
    expect(result.joinType).toBe("LEFT");
    expect(result.leftKey).toBe("some_condition");
    expect(result.strategy).toBe("Broadcast Hash");
  });
});

describe("parseFilterPredicates", () => {
  it("splits on AND at top level", () => {
    const result = parseFilterPredicates("a > 1 AND b < 2");
    expect(result.length).toBe(2);
    expect(result[0]).toBe("a > 1");
    expect(result[1]).toBe("b < 2");
  });

  it("handles single predicate", () => {
    const result = parseFilterPredicates("x = 5");
    expect(result).toEqual(["x = 5"]);
  });
});

describe("parseSortKeys", () => {
  it("extracts column and direction", () => {
    const result = parseSortKeys("col_a ASC, col_b DESC");
    expect(result).toEqual([
      { column: "col_a", direction: "ASC" },
      { column: "col_b", direction: "DESC" },
    ]);
  });

  it("defaults direction to ASC", () => {
    const result = parseSortKeys("col_a");
    expect(result[0].column).toBe("col_a");
    expect(result[0].direction).toBe("ASC");
  });
});

describe("parseProjectColumns", () => {
  it("separates columns from expressions", () => {
    const result = parseProjectColumns("a, b, (a + b) AS total");
    expect(result.columns.length).toBeGreaterThanOrEqual(1);
  });
});

describe("parseAggregateDetail", () => {
  it("extracts group-by and functions from pipe-separated format", () => {
    const result = parseAggregateDetail("by team | sum(amount), count(1)");
    expect(result.groupBy).toEqual(["team"]);
    expect(result.functions).toEqual(["sum(amount)", "count(1)"]);
  });

  it("handles group-by only", () => {
    const result = parseAggregateDetail("by team, region");
    expect(result.groupBy).toEqual(["team", "region"]);
  });
});
