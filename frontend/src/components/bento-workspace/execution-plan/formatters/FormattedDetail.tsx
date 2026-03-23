import { ScanFormatter } from "./ScanFormatter";
import { JoinFormatter } from "./JoinFormatter";
import { FilterFormatter } from "./FilterFormatter";
import { ProjectFormatter } from "./ProjectFormatter";
import { AggregateFormatter } from "./AggregateFormatter";
import { SortFormatter } from "./SortFormatter";
import { ExchangeFormatter } from "./ExchangeFormatter";
import { WindowFormatter } from "./WindowFormatter";
import { LightFormatter } from "./LightFormatter";
import { FallbackFormatter } from "./FallbackFormatter";
import type { ExecutionPlanNode } from "@/types/execution-plan";

const LIGHT_NODES = new Set([
  "union",
  "expand",
  "generate",
  "coalesce",
  "globallimit",
  "locallimit",
  "collectlimit",
  "takeorderedandproject",
]);

export function FormattedDetail({ node }: { node: ExecutionPlanNode }) {
  const lower = node.name.toLowerCase();
  if (lower.includes("scan") || lower.includes("datasource")) {
    return <ScanFormatter node={node} />;
  }
  if (lower.includes("join")) {
    return <JoinFormatter node={node} />;
  }
  if (lower === "filter") {
    return <FilterFormatter node={node} />;
  }
  if (lower === "project") {
    const detail = node.full_detail || node.detail;
    if (detail.includes("|")) return <AggregateFormatter node={node} />;
    return <ProjectFormatter node={node} />;
  }
  if (lower.includes("aggregate") || lower.includes("hashaggregate")) {
    return <AggregateFormatter node={node} />;
  }
  if (lower === "window") {
    return <WindowFormatter node={node} />;
  }
  if (lower.includes("sort") && !lower.includes("merge")) {
    return <SortFormatter node={node} />;
  }
  if (lower.includes("exchange")) {
    return <ExchangeFormatter node={node} />;
  }
  if (LIGHT_NODES.has(lower) || lower.includes("limit")) {
    return <LightFormatter node={node} />;
  }
  return <FallbackFormatter node={node} />;
}
