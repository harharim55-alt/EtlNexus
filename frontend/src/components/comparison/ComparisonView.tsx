import { useMemo } from "react";
import { X, GitCompareArrows, ArrowRight, Equal, Plus, Minus } from "lucide-react";
import { useComparisonStore } from "@/stores/comparison-store";
import { usePipelineDetail } from "@/hooks/use-pipeline-detail";
import { useResourceMetrics } from "@/hooks/use-resource-metrics";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { stripDummy, formatCount } from "@/lib/format";
import type { PipelineDetail, PipelineField } from "@/types/pipeline";
import type { ResourceMetrics } from "@/types/resources";

/* ── Schema Diff Logic ────────────────────────────────────────────── */

interface FieldDiff {
  name: string;
  typeA: string | null;
  typeB: string | null;
  status: "only-a" | "only-b" | "both-same" | "both-different";
}

function computeFieldDiff(
  fieldsA: PipelineField[],
  fieldsB: PipelineField[],
): FieldDiff[] {
  const mapA = new Map(fieldsA.map((f) => [f.name, f.data_type]));
  const mapB = new Map(fieldsB.map((f) => [f.name, f.data_type]));
  const allNames = new Set([...mapA.keys(), ...mapB.keys()]);
  const diffs: FieldDiff[] = [];

  for (const name of allNames) {
    const inA = mapA.has(name);
    const inB = mapB.has(name);
    if (inA && !inB) {
      diffs.push({ name, typeA: mapA.get(name)!, typeB: null, status: "only-a" });
    } else if (!inA && inB) {
      diffs.push({ name, typeA: null, typeB: mapB.get(name)!, status: "only-b" });
    } else {
      const tA = mapA.get(name)!;
      const tB = mapB.get(name)!;
      diffs.push({
        name,
        typeA: tA,
        typeB: tB,
        status: tA === tB ? "both-same" : "both-different",
      });
    }
  }

  // Sort: differences first, then alphabetical
  const order = { "only-a": 0, "only-b": 1, "both-different": 2, "both-same": 3 };
  diffs.sort((a, b) => order[a.status] - order[b.status] || a.name.localeCompare(b.name));
  return diffs;
}

/* ── Sub-components ───────────────────────────────────────────────── */

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-3">
      {children}
    </h3>
  );
}

function MetadataRow({
  label,
  valueA,
  valueB,
}: {
  label: string;
  valueA: React.ReactNode;
  valueB: React.ReactNode;
}) {
  const same = String(valueA) === String(valueB);
  return (
    <div className="grid grid-cols-[1fr_1fr_1fr] gap-4 py-2 border-b border-border last:border-b-0">
      <span className="text-xs text-text-secondary font-medium">{label}</span>
      <span className="text-xs text-text-primary font-mono">{valueA ?? "\u2014"}</span>
      <span
        className={`text-xs font-mono ${same ? "text-text-primary" : "text-amber-400"}`}
      >
        {valueB ?? "\u2014"}
      </span>
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === "success"
      ? "bg-emerald-500"
      : status === "failed"
        ? "bg-rose-500"
        : status === "running"
          ? "bg-blue-500"
          : "bg-slate-500";
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`block h-2 w-2 rounded-full ${color}`} />
      <span className="text-xs text-text-primary capitalize">{status}</span>
    </span>
  );
}

function PipelineHeader({ pipeline }: { pipeline: PipelineDetail }) {
  return (
    <div className="bg-card rounded-xl border border-border p-4">
      <h2 className="text-base font-semibold text-text-heading truncate mb-1">
        {stripDummy(pipeline.name)}
      </h2>
      <div className="flex items-center gap-3 flex-wrap">
        <StatusDot status={pipeline.airflow_status} />
        {pipeline.category && (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            {pipeline.category}
          </span>
        )}
        {pipeline.team && (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-hover-bg text-text-secondary border border-border">
            {pipeline.team}
          </span>
        )}
        <span className="text-[10px] font-mono text-text-muted">
          {pipeline.pipeline_type === "api" ? "API" : "ETL"}
        </span>
      </div>
    </div>
  );
}

function SchemaDiffSection({
  diffs,
  nameA,
  nameB,
}: {
  diffs: FieldDiff[];
  nameA: string;
  nameB: string;
}) {
  const counts = useMemo(() => {
    let onlyA = 0,
      onlyB = 0,
      shared = 0,
      typeDiff = 0;
    for (const d of diffs) {
      if (d.status === "only-a") onlyA++;
      else if (d.status === "only-b") onlyB++;
      else if (d.status === "both-different") typeDiff++;
      else shared++;
    }
    return { onlyA, onlyB, shared, typeDiff };
  }, [diffs]);

  return (
    <div className="bg-card rounded-xl border border-border p-4">
      <SectionHeader>Schema Diff</SectionHeader>

      {/* Summary badges */}
      <div className="flex gap-2 mb-4 flex-wrap">
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <Equal className="inline size-3 mr-1" />
          {counts.shared} shared
        </span>
        {counts.typeDiff > 0 && (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <ArrowRight className="inline size-3 mr-1" />
            {counts.typeDiff} type diff
          </span>
        )}
        {counts.onlyA > 0 && (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <Minus className="inline size-3 mr-1" />
            {counts.onlyA} only in A
          </span>
        )}
        {counts.onlyB > 0 && (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Plus className="inline size-3 mr-1" />
            {counts.onlyB} only in B
          </span>
        )}
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-[1fr_1fr_1fr] gap-4 pb-2 border-b border-border-prominent mb-1">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
          Field
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted truncate">
          {nameA}
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted truncate">
          {nameB}
        </span>
      </div>

      {/* Field rows */}
      <div className="max-h-80 overflow-y-auto">
        {diffs.length === 0 && (
          <p className="text-xs text-text-muted py-4 text-center">No fields to compare</p>
        )}
        {diffs.map((d) => {
          const rowColor =
            d.status === "only-a"
              ? "bg-rose-500/5"
              : d.status === "only-b"
                ? "bg-emerald-500/5"
                : d.status === "both-different"
                  ? "bg-amber-500/5"
                  : "";
          return (
            <div
              key={d.name}
              className={`grid grid-cols-[1fr_1fr_1fr] gap-4 py-1.5 border-b border-border last:border-b-0 ${rowColor}`}
            >
              <span className="text-xs text-text-primary font-mono truncate">{d.name}</span>
              <span
                className={`text-xs font-mono ${d.typeA ? "text-text-secondary" : "text-text-faint"}`}
              >
                {d.typeA ?? "\u2014"}
              </span>
              <span
                className={`text-xs font-mono ${
                  d.status === "both-different"
                    ? "text-amber-400"
                    : d.typeB
                      ? "text-text-secondary"
                      : "text-text-faint"
                }`}
              >
                {d.typeB ?? "\u2014"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MetadataSection({
  a,
  b,
}: {
  a: PipelineDetail;
  b: PipelineDetail;
}) {
  const fmtRows = (v: string | null) => {
    if (!v) return "\u2014";
    const n = Number(v);
    return isNaN(n) ? v : `${formatCount(n)} rows/day`;
  };

  return (
    <div className="bg-card rounded-xl border border-border p-4">
      <SectionHeader>Metadata</SectionHeader>
      <MetadataRow label="Schedule" valueA={a.schedule} valueB={b.schedule} />
      <MetadataRow label="Rows/Day" valueA={fmtRows(a.rows_per_day)} valueB={fmtRows(b.rows_per_day)} />
      <MetadataRow label="Type" valueA={a.pipeline_type} valueB={b.pipeline_type} />
      <MetadataRow
        label="Source Tables"
        valueA={a.source_tables.length > 0 ? a.source_tables.join(", ") : "\u2014"}
        valueB={b.source_tables.length > 0 ? b.source_tables.join(", ") : "\u2014"}
      />
      <MetadataRow
        label="Dest Tables"
        valueA={a.destination_tables.length > 0 ? a.destination_tables.join(", ") : "\u2014"}
        valueB={b.destination_tables.length > 0 ? b.destination_tables.join(", ") : "\u2014"}
      />
    </div>
  );
}

function ResourceSection({
  metricsA,
  metricsB,
  loadingA,
  loadingB,
}: {
  metricsA: ResourceMetrics | undefined;
  metricsB: ResourceMetrics | undefined;
  loadingA: boolean;
  loadingB: boolean;
}) {
  if (loadingA || loadingB) {
    return (
      <div className="bg-card rounded-xl border border-border p-4">
        <SectionHeader>Resource Config</SectionHeader>
        <Skeleton className="h-20 w-full bg-hover-bg rounded-lg" />
      </div>
    );
  }

  const cfgA = metricsA?.resource_configs?.[0];
  const cfgB = metricsB?.resource_configs?.[0];

  if (!cfgA && !cfgB) return null;

  return (
    <div className="bg-card rounded-xl border border-border p-4">
      <SectionHeader>Resource Config</SectionHeader>
      <MetadataRow
        label="Driver Memory"
        valueA={cfgA?.spark_driver_memory ?? "\u2014"}
        valueB={cfgB?.spark_driver_memory ?? "\u2014"}
      />
      <MetadataRow
        label="Executor Memory"
        valueA={cfgA?.spark_executor_memory ?? "\u2014"}
        valueB={cfgB?.spark_executor_memory ?? "\u2014"}
      />
      <MetadataRow
        label="Executor Cores"
        valueA={cfgA?.spark_executor_cores ?? "\u2014"}
        valueB={cfgB?.spark_executor_cores ?? "\u2014"}
      />
      <MetadataRow
        label="Num Executors"
        valueA={cfgA?.spark_num_executors ?? "\u2014"}
        valueB={cfgB?.spark_num_executors ?? "\u2014"}
      />
      <MetadataRow
        label="Success Rate"
        valueA={metricsA?.success_rate != null ? `${metricsA.success_rate}%` : "\u2014"}
        valueB={metricsB?.success_rate != null ? `${metricsB.success_rate}%` : "\u2014"}
      />
      <MetadataRow
        label="Avg Duration"
        valueA={
          metricsA?.avg_duration_seconds != null
            ? `${Math.round(metricsA.avg_duration_seconds)}s`
            : "\u2014"
        }
        valueB={
          metricsB?.avg_duration_seconds != null
            ? `${Math.round(metricsB.avg_duration_seconds)}s`
            : "\u2014"
        }
      />
      <MetadataRow
        label="Run Count"
        valueA={metricsA?.run_count ?? "\u2014"}
        valueB={metricsB?.run_count ?? "\u2014"}
      />
    </div>
  );
}

/* ── Main ComparisonView ─────────────────────────────────────────── */

export function ComparisonView() {
  const pipelineA = useComparisonStore((s) => s.pipelineA);
  const pipelineB = useComparisonStore((s) => s.pipelineB);
  const clearComparison = useComparisonStore((s) => s.clearComparison);

  const { data: detailA, isLoading: loadA } = usePipelineDetail(pipelineA);
  const { data: detailB, isLoading: loadB } = usePipelineDetail(pipelineB);
  const { data: resA, isLoading: resLoadA } = useResourceMetrics(pipelineA);
  const { data: resB, isLoading: resLoadB } = useResourceMetrics(pipelineB);

  const fieldDiffs = useMemo(
    () =>
      detailA && detailB
        ? computeFieldDiff(detailA.fields, detailB.fields)
        : [],
    [detailA, detailB],
  );

  const loading = loadA || loadB;

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-border bg-background shrink-0">
        <div className="flex items-center gap-3">
          <GitCompareArrows className="size-5 text-indigo-400" />
          <h1 className="text-sm font-semibold text-text-heading">Pipeline Comparison</h1>
          {detailA && detailB && (
            <span className="text-xs text-text-muted font-mono">
              {stripDummy(detailA.name)}
              <ArrowRight className="inline size-3 mx-1.5 text-text-faint" />
              {stripDummy(detailB.name)}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={clearComparison}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-secondary hover:text-text-primary bg-hover-bg hover:bg-hover-bg-strong rounded-lg border border-border transition-colors cursor-pointer"
        >
          <X className="size-3.5" />
          Close Comparison
        </button>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6 max-w-5xl mx-auto">
          {loading ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Skeleton className="h-24 bg-hover-bg rounded-xl" />
                <Skeleton className="h-24 bg-hover-bg rounded-xl" />
              </div>
              <Skeleton className="h-48 bg-hover-bg rounded-xl" />
              <Skeleton className="h-32 bg-hover-bg rounded-xl" />
            </div>
          ) : detailA && detailB ? (
            <>
              {/* Headers side by side */}
              <div className="grid grid-cols-2 gap-4">
                <PipelineHeader pipeline={detailA} />
                <PipelineHeader pipeline={detailB} />
              </div>

              {/* Schema diff */}
              <SchemaDiffSection
                diffs={fieldDiffs}
                nameA={stripDummy(detailA.name)}
                nameB={stripDummy(detailB.name)}
              />

              {/* Metadata comparison */}
              <MetadataSection a={detailA} b={detailB} />

              {/* Resource comparison */}
              <ResourceSection
                metricsA={resA}
                metricsB={resB}
                loadingA={resLoadA}
                loadingB={resLoadB}
              />
            </>
          ) : (
            <div className="flex items-center justify-center h-64">
              <p className="text-sm text-text-muted">
                Select two pipelines to compare.
              </p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
