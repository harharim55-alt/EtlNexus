import { describe, it, expect } from "vitest";
import { groupByDag, groupByTaskGroup, statusSummary } from "@/components/bento-workspace/lineage/lineage-utils";
import type { TopologyTask } from "@/types/topology";

function makeTask(overrides: Partial<TopologyTask> = {}): TopologyTask {
  return {
    task_id: "task_1",
    pipeline_name: null,
    pipeline_id: null,
    status: "success",
    dag_id: "dag_a",
    task_group_id: null,
    ...overrides,
  };
}

describe("groupByDag", () => {
  it("groups tasks by dag_id", () => {
    const tasks = [
      makeTask({ task_id: "t1", dag_id: "dag_a" }),
      makeTask({ task_id: "t2", dag_id: "dag_b" }),
      makeTask({ task_id: "t3", dag_id: "dag_a" }),
    ];
    const groups = groupByDag(tasks);
    expect(Object.keys(groups)).toEqual(["dag_a", "dag_b"]);
    expect(groups.dag_a).toHaveLength(2);
    expect(groups.dag_b).toHaveLength(1);
  });

  it("uses 'unassigned' for empty dag_id", () => {
    const tasks = [makeTask({ task_id: "t1", dag_id: "" })];
    const groups = groupByDag(tasks);
    expect(groups.unassigned).toHaveLength(1);
  });

  it("returns empty object for empty array", () => {
    expect(groupByDag([])).toEqual({});
  });

  it("works with generic types", () => {
    const items = [
      { dag_id: "x", extra: 1 },
      { dag_id: "x", extra: 2 },
      { dag_id: "y", extra: 3 },
    ];
    const groups = groupByDag(items);
    expect(groups.x).toHaveLength(2);
    expect(groups.y).toHaveLength(1);
    expect(groups.x[0].extra).toBe(1);
  });
});

describe("groupByTaskGroup", () => {
  it("groups tasks by task_group_id", () => {
    const tasks = [
      makeTask({ task_id: "t1", task_group_id: "group_a" }),
      makeTask({ task_id: "t2", task_group_id: "group_b" }),
      makeTask({ task_id: "t3", task_group_id: "group_a" }),
    ];
    const { grouped, hasGroups } = groupByTaskGroup(tasks);
    expect(hasGroups).toBe(true);
    expect(grouped.group_a).toHaveLength(2);
    expect(grouped.group_b).toHaveLength(1);
  });

  it("puts ungrouped tasks under _ungrouped", () => {
    const tasks = [
      makeTask({ task_id: "t1", task_group_id: null }),
      makeTask({ task_id: "t2", task_group_id: "group_a" }),
    ];
    const { grouped, hasGroups } = groupByTaskGroup(tasks);
    expect(hasGroups).toBe(true);
    expect(grouped._ungrouped).toHaveLength(1);
    expect(grouped.group_a).toHaveLength(1);
  });

  it("returns hasGroups=false when no task_group_ids", () => {
    const tasks = [
      makeTask({ task_id: "t1", task_group_id: null }),
      makeTask({ task_id: "t2", task_group_id: null }),
    ];
    const { hasGroups } = groupByTaskGroup(tasks);
    expect(hasGroups).toBe(false);
  });
});

describe("statusSummary", () => {
  it("counts tasks by status", () => {
    const tasks = [
      makeTask({ task_id: "t1", status: "success" }),
      makeTask({ task_id: "t2", status: "failed" }),
      makeTask({ task_id: "t3", status: "success" }),
    ];
    const summary = statusSummary(tasks);
    expect(summary).toEqual({ success: 2, failed: 1 });
  });

  it("uses 'unknown' for empty status", () => {
    const tasks = [makeTask({ task_id: "t1", status: "" })];
    const summary = statusSummary(tasks);
    expect(summary).toEqual({ unknown: 1 });
  });

  it("returns empty object for empty array", () => {
    expect(statusSummary([])).toEqual({});
  });
});
