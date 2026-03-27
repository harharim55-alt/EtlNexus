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
import { SetOperationFormatter } from "./SetOperationFormatter";
import { DeduplicateFormatter } from "./DeduplicateFormatter";
import { SampleFormatter } from "./SampleFormatter";
import { RangeFormatter } from "./RangeFormatter";
import { CacheFormatter } from "./CacheFormatter";
import { PythonUDFFormatter } from "./PythonUDFFormatter";
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
  // Phase 1C: infrastructure nodes
  "subqueryexec",
  "subquerybroadcast",
  "collectmetrics",
  "mappartitions",
  "mapelements",
  "unpivot",
  // Phase 3B: write operations
  "overwritepartitionsdynamic",
  "writefiles",
]);

export function FormattedDetail({ node }: { node: ExecutionPlanNode }) {
  const lower = node.name.toLowerCase();

  // Phase 1A: Set operations, Dedup, Sample
  if (
    lower === "except" ||
    lower === "exceptall" ||
    lower === "intersect" ||
    lower === "intersectall"
  ) {
    return <SetOperationFormatter node={node} />;
  }
  if (lower === "deduplicate") {
    return <DeduplicateFormatter node={node} />;
  }
  if (lower === "sample") {
    return <SampleFormatter node={node} />;
  }

  // Phase 1B: Data source nodes
  if (lower.includes("inmemory")) {
    return <CacheFormatter node={node} />;
  }
  if (lower === "range") {
    return <RangeFormatter node={node} />;
  }

  // Phase 1D: Python/Pandas UDF nodes
  if (
    lower.includes("python") ||
    lower.includes("flatmapgroups") ||
    lower.includes("arroweval") ||
    lower.includes("batcheval")
  ) {
    return <PythonUDFFormatter node={node} />;
  }

  // Existing dispatchers
  if (lower.includes("scan") || lower.includes("datasource")) {
    return <ScanFormatter node={node} />;
  }
  if (lower.includes("join") || lower === "cartesianproduct") {
    return <JoinFormatter node={node} />;
  }
  if (lower === "filter") {
    return <FilterFormatter node={node} />;
  }
  if (lower === "project") {
    const detail = node.full_detail || node.detail;
    // Check for structured format with passthrough:/renamed:/computed: markers
    if (
      detail.includes("passthrough:") ||
      detail.includes("renamed:") ||
      detail.includes("computed:")
    ) {
      return <ProjectFormatter node={node} />;
    }
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
