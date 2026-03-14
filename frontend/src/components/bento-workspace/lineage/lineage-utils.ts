import type { TopologyTask, TopologyBouncer } from "@/types/topology";

export function groupBouncersByDag(
  bouncers: TopologyBouncer[],
): Record<string, TopologyBouncer[]> {
  const groups: Record<string, TopologyBouncer[]> = {};
  for (const s of bouncers) {
    for (const dagId of s.dag_ids) {
      if (!groups[dagId]) groups[dagId] = [];
      groups[dagId].push(s);
    }
  }
  return groups;
}

export function groupByDag<T extends { dag_id: string }>(tasks: T[]): Record<string, T[]> {
  const groups: Record<string, T[]> = {};
  for (const t of tasks) {
    const key = t.dag_id || "unassigned";
    if (!groups[key]) groups[key] = [];
    groups[key].push(t);
  }
  return groups;
}

export function groupByTaskGroup(
  tasks: TopologyTask[],
): { grouped: Record<string, TopologyTask[]>; hasGroups: boolean } {
  const groups: Record<string, TopologyTask[]> = {};
  let hasGroups = false;
  for (const t of tasks) {
    const key = t.task_group_id || "_ungrouped";
    if (t.task_group_id) hasGroups = true;
    if (!groups[key]) groups[key] = [];
    groups[key].push(t);
  }
  return { grouped: groups, hasGroups };
}

export function statusSummary(tasks: TopologyTask[]) {
  const counts: Record<string, number> = {};
  for (const t of tasks) {
    const s = t.status || "unknown";
    counts[s] = (counts[s] || 0) + 1;
  }
  return counts;
}
