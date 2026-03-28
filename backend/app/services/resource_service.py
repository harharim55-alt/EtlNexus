"""Resource service — reads allocated configs and run history from DB."""

import copy
import hashlib
import json
import logging
import re
import uuid
from datetime import datetime

from app.config import settings
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.resource_repo import ResourceRepository
from app.repositories.resource_stats import ResourceStatsBuilder
from app.schemas.execution_plan import PlanDiffNode, PlanDiffResponse
from app.schemas.resources import (
    ActualUsage,
    CapacityBar,
    DurationRun,
    FieldSnapshot,
    PipelineRunDetail,
    PipelineRunsResponse,
    ResourceConfigEntry,
    ResourceHistoryRecord,
    ResourceHistoryResponse,
    ResourceMetricsResponse,
    ResourceRecommendation,
    TrendAnalysis,
)

logger = logging.getLogger(__name__)


class ResourceService:
    def __init__(
        self,
        resource_repo: ResourceRepository,
        pipeline_repo: PipelineRepository,
    ):
        self.resource_repo = resource_repo
        self.pipeline_repo = pipeline_repo
        self.stats = ResourceStatsBuilder(resource_repo.session)

    async def get_resource_metrics(
        self,
        pipeline_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ResourceMetricsResponse | None:
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        # Allocated configs (per DAG)
        configs = await self.resource_repo.get_configs_by_pipeline(pipeline_id)

        # Run history + stats
        runs = await self.resource_repo.get_recent_runs(
            pipeline_id, limit=20, date_from=date_from, date_to=date_to,
        )
        stats = await self.stats.get_run_stats(
            pipeline_id, date_from=date_from, date_to=date_to,
        )

        # Build response
        resource_configs = [
            ResourceConfigEntry(
                dag_id=c.dag_id,
                spark_driver_memory=c.spark_driver_memory,
                spark_executor_memory=c.spark_executor_memory,
                spark_executor_cores=c.spark_executor_cores,
                spark_num_executors=c.spark_num_executors,
                is_dag_override=c.is_dag_override,
            )
            for c in configs
        ]

        recent_runs = [
            DurationRun(
                duration_seconds=r.duration_seconds or 0,
                execution_date=r.start_date.isoformat() if r.start_date else None,
                status=r.status,
                dag_id=r.dag_id,
                spark_application_id=r.spark_application_id,
                metrics_source=r.metrics_source,
            )
            for r in runs
            if r.duration_seconds is not None
        ]

        # Determine dominant metrics source from recent runs
        source_counts: dict[str, int] = {}
        for r in runs:
            if r.metrics_source:
                source_counts[r.metrics_source] = source_counts.get(r.metrics_source, 0) + 1
        dominant_source = max(source_counts, key=source_counts.get) if source_counts else None

        actual_usage = ActualUsage(
            avg_driver_memory_used_mb=stats.get("avg_driver_mem_used_mb"),
            avg_executor_memory_peak_mb=stats.get("avg_executor_mem_peak_mb"),
            avg_cpu_utilization_pct=stats.get("avg_cpu_pct"),
            avg_executors_active=stats.get("avg_executors_active"),
            avg_jvm_gc_time_ms=stats.get("avg_jvm_gc_time_ms"),
            avg_shuffle_read_bytes=stats.get("avg_shuffle_read_bytes"),
            avg_shuffle_write_bytes=stats.get("avg_shuffle_write_bytes"),
            avg_input_bytes=stats.get("avg_input_bytes"),
            avg_output_bytes=stats.get("avg_output_bytes"),
            avg_memory_bytes_spilled=stats.get("avg_memory_bytes_spilled"),
            avg_disk_bytes_spilled=stats.get("avg_disk_bytes_spilled"),
            avg_peak_execution_memory=stats.get("avg_peak_execution_memory"),
            peak_driver_memory_used_mb=stats.get("peak_driver_mem_used_mb"),
            peak_executor_memory_mb=stats.get("peak_executor_mem_mb"),
            peak_cpu_utilization_pct=stats.get("peak_cpu_pct"),
            peak_executors_active=stats.get("peak_executors_active"),
            peak_execution_memory=stats.get("peak_execution_memory"),
            metrics_source=dominant_source,
        )

        # Find latest duration
        latest_duration = None
        if runs:
            for r in runs:
                if r.duration_seconds is not None:
                    latest_duration = r.duration_seconds
                    break

        capacity = self._compute_capacity(configs, actual_usage)
        recommendations = self._compute_recommendations(configs, actual_usage, stats)
        trends = self._compute_trends(runs)

        return ResourceMetricsResponse(
            avg_duration_seconds=stats.get("avg_duration"),
            min_duration_seconds=stats.get("min_duration"),
            max_duration_seconds=stats.get("max_duration"),
            latest_duration_seconds=latest_duration,
            recent_runs=recent_runs,
            run_count=stats.get("run_count", 0),
            success_rate=stats.get("success_rate"),
            resource_configs=resource_configs,
            actual_usage=actual_usage,
            capacity=capacity,
            # Percentile stats
            p50_duration_seconds=stats.get("p50_duration"),
            p95_duration_seconds=stats.get("p95_duration"),
            p99_duration_seconds=stats.get("p99_duration"),
            p95_driver_memory_mb=stats.get("p95_driver_mem"),
            p95_executor_memory_mb=stats.get("p95_executor_mem"),
            p95_cpu_pct=stats.get("p95_cpu"),
            # Insights
            recommendations=recommendations,
            trends=trends,
            avg_input_bytes=stats.get("avg_input_bytes"),
        )

    async def get_resource_history(
        self,
        pipeline_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ResourceHistoryResponse | None:
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        runs, total = await self.stats.get_resource_history(
            pipeline_id, date_from=date_from, date_to=date_to,
        )

        records = [
            ResourceHistoryRecord(
                execution_date=r.start_date.isoformat() if r.start_date else None,
                dag_id=r.dag_id,
                dag_run_id=r.dag_run_id,
                status=r.status,
                duration_seconds=r.duration_seconds,
                driver_memory_used_mb=r.driver_memory_used_mb,
                executor_memory_peak_mb=r.executor_memory_peak_mb,
                cpu_utilization_pct=r.cpu_utilization_pct,
                executors_active=r.executors_active,
                peak_execution_memory=r.peak_execution_memory,
                jvm_gc_time_ms=r.jvm_gc_time_ms,
                shuffle_read_bytes=r.shuffle_read_bytes,
                shuffle_write_bytes=r.shuffle_write_bytes,
                input_bytes=r.input_bytes,
                output_bytes=r.output_bytes,
                memory_bytes_spilled=r.memory_bytes_spilled,
                disk_bytes_spilled=r.disk_bytes_spilled,
                metrics_source=r.metrics_source,
            )
            for r in runs
        ]

        return ResourceHistoryResponse(records=records, total=total)

    async def get_execution_plan(
        self,
        pipeline_id: uuid.UUID,
        dag_run_id: str | None = None,
    ) -> dict | None:
        """Get a specific or latest execution plan for a pipeline."""
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        if dag_run_id:
            run = await self.resource_repo.get_execution_plan_by_run(
                pipeline_id, dag_run_id,
            )
        else:
            run = await self.resource_repo.get_latest_execution_plan(pipeline_id)

        if not run or not run.execution_plan:
            return None

        try:
            plan_data = json.loads(run.execution_plan)
        except (json.JSONDecodeError, TypeError):
            return None

        plan_hash = self._compute_plan_hash(plan_data)
        # Annotate a deep copy so the original parsed data is not mutated
        annotated_plan = copy.deepcopy(plan_data)
        self._annotate_bottlenecks(annotated_plan)

        # Compute plan stability by comparing hashes of the last few plans
        plan_stability = await self._compute_plan_stability(pipeline_id, plan_hash)

        return {
            "dag_id": run.dag_id,
            "dag_run_id": run.dag_run_id,
            "task_id": pipeline.task_id or pipeline.name,
            "status": run.status,
            "duration_seconds": run.duration_seconds,
            "execution_date": run.start_date.isoformat() if run.start_date else None,
            "execution_plan": annotated_plan,
            "plan_hash": plan_hash,
            "plan_stability": plan_stability,
        }

    async def get_execution_plan_runs(
        self,
        pipeline_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        """List paginated runs that have execution plans."""
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return {"items": [], "total": 0}
        items, total = await self.resource_repo.get_execution_plan_runs(
            pipeline_id, skip=skip, limit=limit,
        )
        return {"items": items, "total": total}

    async def get_pipeline_runs(
        self,
        pipeline_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> PipelineRunsResponse:
        """List all runs for a pipeline, paginated."""
        items, total = await self.resource_repo.get_all_runs(
            pipeline_id, skip=skip, limit=limit,
        )
        return PipelineRunsResponse(items=items, total=total)

    async def get_run_detail(
        self,
        pipeline_id: uuid.UUID,
        dag_run_id: str,
    ) -> PipelineRunDetail | None:
        """Get full detail for a single run."""
        run = await self.resource_repo.get_run_by_id(pipeline_id, dag_run_id)
        if not run:
            return None

        fields_snapshot = None
        if run.fields_snapshot:
            fields_snapshot = [
                FieldSnapshot(**f) if isinstance(f, dict) else f
                for f in run.fields_snapshot
            ]

        return PipelineRunDetail(
            dag_run_id=run.dag_run_id,
            dag_id=run.dag_id,
            status=run.status,
            start_date=run.start_date,
            end_date=run.end_date,
            duration_seconds=run.duration_seconds,
            driver_memory_used_mb=run.driver_memory_used_mb,
            executor_memory_peak_mb=run.executor_memory_peak_mb,
            cpu_utilization_pct=run.cpu_utilization_pct,
            executors_active=run.executors_active,
            peak_execution_memory=run.peak_execution_memory,
            jvm_gc_time_ms=run.jvm_gc_time_ms,
            shuffle_read_bytes=run.shuffle_read_bytes,
            shuffle_write_bytes=run.shuffle_write_bytes,
            input_bytes=run.input_bytes,
            output_bytes=run.output_bytes,
            memory_bytes_spilled=run.memory_bytes_spilled,
            disk_bytes_spilled=run.disk_bytes_spilled,
            metrics_source=run.metrics_source,
            spark_application_id=run.spark_application_id,
            has_execution_plan=run.execution_plan is not None,
            fields_snapshot=fields_snapshot,
            source_tables_snapshot=run.source_tables_snapshot,
            destination_tables_snapshot=run.destination_tables_snapshot,
            failure_reason=getattr(run, "failure_reason", None),
        )

    @staticmethod
    def _make_capacity_bar(
        label: str,
        alloc_numeric: float,
        allocated_label: str,
        used_raw: float,
        max_val: float,
        *,
        format_as_memory: bool = False,
    ) -> CapacityBar:
        """Build a single ``CapacityBar`` from pre-computed values.

        Args:
            label: Human-readable resource label (e.g. ``"Driver Memory"``).
            alloc_numeric: Allocated amount as a float in the same unit as
                ``max_val`` (used for percentage calculation).
            allocated_label: Display string for the allocated amount (e.g.
                the raw config string ``"8g"`` or a stringified integer).
            used_raw: Observed peak usage in the same unit as ``max_val``.
            max_val: Cluster-wide maximum for this resource.
            format_as_memory: When ``True`` the ``used`` label is formatted as
                ``"{used_raw:.1f}g"`` and ``max_capacity`` as ``"{max_val}g"``;
                otherwise both are stringified as integers.

        Returns:
            A populated :class:`CapacityBar` instance.
        """
        used_str = (
            f"{used_raw:.1f}g" if format_as_memory and used_raw
            else (str(int(used_raw)) if used_raw else "—")
        )
        return CapacityBar(
            label=label,
            allocated=allocated_label,
            used=used_str,
            max_capacity=f"{max_val}g" if format_as_memory else str(int(max_val)),
            allocated_pct=round((alloc_numeric / max_val) * 100, 1) if max_val else 0,
            used_pct=round((used_raw / max_val) * 100, 1) if max_val else 0,
        )

    def _compute_capacity(
        self,
        configs: list,
        actual_usage: ActualUsage,
    ) -> list[CapacityBar]:
        """Compute capacity bars using the largest allocated config."""
        if not configs:
            return []

        # Find the largest config (prefer non-override, or just the first)
        best = configs[0]
        for c in configs:
            if not c.is_dag_override:
                best = c
                break

        bars: list[CapacityBar] = []

        # Driver Memory — use peak values for capacity
        if best.spark_driver_memory:
            alloc_gb = self._parse_memory_gb(best.spark_driver_memory)
            max_gb = settings.spark_max_driver_memory_gb
            used_gb = (
                actual_usage.peak_driver_memory_used_mb / 1024
                if actual_usage.peak_driver_memory_used_mb
                else 0.0
            )
            bars.append(self._make_capacity_bar(
                "Driver Memory", alloc_gb, best.spark_driver_memory, used_gb, max_gb,
                format_as_memory=True,
            ))

        # Executor Memory — use peak values for capacity
        if best.spark_executor_memory:
            alloc_gb = self._parse_memory_gb(best.spark_executor_memory)
            max_gb = settings.spark_max_executor_memory_gb
            used_gb = (
                actual_usage.peak_executor_memory_mb / 1024
                if actual_usage.peak_executor_memory_mb
                else 0.0
            )
            bars.append(self._make_capacity_bar(
                "Executor Memory", alloc_gb, best.spark_executor_memory, used_gb, max_gb,
                format_as_memory=True,
            ))

        # Executor Cores — use peak CPU for capacity
        if best.spark_executor_cores:
            alloc = float(best.spark_executor_cores)
            max_val = float(settings.spark_max_executor_cores)
            used = float(
                round(alloc * (actual_usage.peak_cpu_utilization_pct / 100))
                if actual_usage.peak_cpu_utilization_pct
                else 0
            )
            bars.append(self._make_capacity_bar(
                "CPU Cores", alloc, str(best.spark_executor_cores), used, max_val,
            ))

        # Num Executors — use peak for capacity
        if best.spark_num_executors:
            alloc = float(best.spark_num_executors)
            max_val = float(settings.spark_max_total_executors)
            used = float(actual_usage.peak_executors_active or 0)
            bars.append(self._make_capacity_bar(
                "Executors", alloc, str(best.spark_num_executors), used, max_val,
            ))

        return bars

    @staticmethod
    def _parse_memory_gb(mem_str: str) -> float:
        """Parse memory string to GB. E.g., '8g' -> 8.0, '512m' -> 0.5."""
        match = re.match(r"^(\d+(?:\.\d+)?)\s*([gmtGMT]?)$", mem_str.strip())
        if not match:
            return 0
        val = float(match.group(1))
        unit = match.group(2).lower()
        if unit == "m":
            return val / 1024
        if unit == "t":
            return val * 1024
        return val  # default is GB

    @staticmethod
    def _annotate_bottlenecks(plan_data: dict) -> None:
        """Recursively walk the plan tree dict and flag bottleneck nodes in-place.

        A node is considered a bottleneck when its metrics indicate:
        - Row count exceeds 10 million rows, or
        - Shuffle bytes exceed 1 GB.

        Args:
            plan_data: Mutable plan node dict (modified in place).
        """
        if not isinstance(plan_data, dict):
            return

        metrics = plan_data.get("metrics", {})
        reasons: list[str] = []

        # Check row count
        rows_raw = metrics.get("number of output rows", metrics.get("rows", ""))
        if rows_raw:
            rows_str = str(rows_raw).replace(",", "").strip()
            try:
                rows = int(rows_str)
                if rows > 10_000_000:
                    reasons.append(f"High row count: {rows_raw}")
            except ValueError:
                pass

        # Check shuffle bytes
        for key in ("shuffle bytes written", "shuffle read bytes", "data size"):
            shuffle_raw = metrics.get(key, "")
            if shuffle_raw:
                # Parse values like "1.5 GB", "2048 MB", "512 KB"
                m = re.match(r"([\d.]+)\s*(B|KB|MB|GB|TB)", str(shuffle_raw), re.IGNORECASE)
                if m:
                    value = float(m.group(1))
                    unit = m.group(2).upper()
                    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
                    bytes_val = value * multipliers.get(unit, 1)
                    if bytes_val > 1024**3:  # > 1 GB
                        reasons.append(f"High shuffle: {shuffle_raw}")
                        break

        if reasons:
            plan_data["is_bottleneck"] = True
            plan_data["bottleneck_reason"] = "; ".join(reasons)
        # Do not add keys when not a bottleneck — Pydantic model defaults handle that

        for child in plan_data.get("children", []):
            ResourceService._annotate_bottlenecks(child)

    @staticmethod
    def _compute_plan_hash(plan_data: dict) -> str:
        """Compute a stable SHA-256 hash of the plan tree topology.

        Only node names and types are hashed (metrics are ignored) so that the
        hash reflects the logical plan shape rather than runtime values.

        Args:
            plan_data: Plan node dict (not mutated).

        Returns:
            Hex-encoded SHA-256 digest string.
        """
        def _collect_tokens(node: dict) -> list[str]:
            if not isinstance(node, dict):
                return []
            tokens = [node.get("name", ""), node.get("type", "")]
            for child in node.get("children", []):
                tokens.extend(_collect_tokens(child))
            return tokens

        tokens = _collect_tokens(plan_data)
        content = "|".join(tokens)
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def _compute_recommendations(
        configs: list,
        actual_usage: ActualUsage,
        stats: dict,
    ) -> list[ResourceRecommendation]:
        """Generate resource sizing recommendations by comparing allocated vs peak usage.

        Rules:
        - If peak usage < 50% of allocated, recommend halving the resource.
        - If peak usage > 90% of allocated, warn about OOM/starvation risk.

        Args:
            configs: List of ``PipelineResourceConfig`` ORM objects.
            actual_usage: Aggregated actual usage schema.
            stats: Raw stats dict from ``ResourceStatsBuilder.get_run_stats()``.

        Returns:
            List of :class:`ResourceRecommendation` instances (may be empty).
        """
        if not configs:
            return []

        best = configs[0]
        for c in configs:
            if not c.is_dag_override:
                best = c
                break

        recs: list[ResourceRecommendation] = []

        # Driver memory
        if best.spark_driver_memory and actual_usage.peak_driver_memory_used_mb:
            alloc_mb = ResourceService._parse_memory_gb(best.spark_driver_memory) * 1024
            peak_mb = actual_usage.peak_driver_memory_used_mb
            if alloc_mb > 0:
                ratio = peak_mb / alloc_mb
                if ratio < 0.5:
                    half_gb = alloc_mb / 2 / 1024
                    recs.append(ResourceRecommendation(
                        resource="Driver Memory",
                        current_value=best.spark_driver_memory,
                        recommended_value=f"{half_gb:.0f}g",
                        reason=f"Peak usage is only {ratio * 100:.0f}% of allocated — halving would save resources.",
                        severity="info",
                    ))
                elif ratio > 0.9:
                    recs.append(ResourceRecommendation(
                        resource="Driver Memory",
                        current_value=best.spark_driver_memory,
                        recommended_value=f"{alloc_mb * 1.5 / 1024:.0f}g",
                        reason=f"Peak usage is {ratio * 100:.0f}% of allocated — at risk of OOM.",
                        severity="warning",
                    ))

        # Executor memory
        if best.spark_executor_memory and actual_usage.peak_executor_memory_mb:
            alloc_mb = ResourceService._parse_memory_gb(best.spark_executor_memory) * 1024
            peak_mb = actual_usage.peak_executor_memory_mb
            if alloc_mb > 0:
                ratio = peak_mb / alloc_mb
                if ratio < 0.5:
                    half_gb = alloc_mb / 2 / 1024
                    recs.append(ResourceRecommendation(
                        resource="Executor Memory",
                        current_value=best.spark_executor_memory,
                        recommended_value=f"{half_gb:.0f}g",
                        reason=f"Peak usage is only {ratio * 100:.0f}% of allocated — halving would save resources.",
                        severity="info",
                    ))
                elif ratio > 0.9:
                    recs.append(ResourceRecommendation(
                        resource="Executor Memory",
                        current_value=best.spark_executor_memory,
                        recommended_value=f"{alloc_mb * 1.5 / 1024:.0f}g",
                        reason=f"Peak usage is {ratio * 100:.0f}% of allocated — at risk of OOM.",
                        severity="warning",
                    ))

        return recs

    @staticmethod
    def _compute_trends(recent_runs: list) -> list[TrendAnalysis]:
        """Compute linear regression trends for key metrics over recent runs.

        Uses pure Python (no numpy) to fit a simple least-squares line to
        each metric series ordered by start_date. Only series with at least
        3 data points are analysed.

        Args:
            recent_runs: List of ``PipelineRunHistory`` ORM objects ordered
                by start_date descending (as returned by ``get_recent_runs``).

        Returns:
            List of :class:`TrendAnalysis` instances for metrics that have
            sufficient data, ordered by metric name.
        """
        # Reverse to chronological order for regression
        runs_chron = list(reversed(recent_runs))

        metrics_series: dict[str, list[tuple[float, float]]] = {
            "duration_seconds": [],
            "driver_memory_mb": [],
            "executor_memory_mb": [],
            "cpu_pct": [],
        }

        for i, run in enumerate(runs_chron):
            x = float(i)
            try:
                if run.duration_seconds is not None:
                    metrics_series["duration_seconds"].append((x, float(run.duration_seconds)))
                if run.driver_memory_used_mb is not None:
                    metrics_series["driver_memory_mb"].append((x, float(run.driver_memory_used_mb)))
                if run.executor_memory_peak_mb is not None:
                    metrics_series["executor_memory_mb"].append((x, float(run.executor_memory_peak_mb)))
                if run.cpu_utilization_pct is not None:
                    metrics_series["cpu_pct"].append((x, float(run.cpu_utilization_pct)))
            except (TypeError, ValueError):
                # Skip runs where metric attributes are not numeric
                continue

        trends: list[TrendAnalysis] = []
        for metric, series in metrics_series.items():
            if len(series) < 3:
                continue

            n = len(series)
            sum_x = sum(p[0] for p in series)
            sum_y = sum(p[1] for p in series)
            sum_xy = sum(p[0] * p[1] for p in series)
            sum_x2 = sum(p[0] ** 2 for p in series)

            denom = n * sum_x2 - sum_x ** 2
            if denom == 0:
                continue

            slope = (n * sum_xy - sum_x * sum_y) / denom
            intercept = (sum_y - slope * sum_x) / n

            # Compute R² as a proxy for confidence
            y_mean = sum_y / n
            ss_tot = sum((p[1] - y_mean) ** 2 for p in series)
            if ss_tot == 0:
                r_squared = 1.0
            else:
                ss_res = sum((p[1] - (slope * p[0] + intercept)) ** 2 for p in series)
                r_squared = max(0.0, 1.0 - ss_res / ss_tot)

            # Normalise slope to "per day" assuming runs occur daily on average
            slope_per_day = slope

            if abs(slope_per_day) < 0.01 * (sum_y / n) or abs(slope_per_day) < 1e-6:
                direction = "stable"
            elif slope_per_day > 0:
                direction = "increasing"
            else:
                direction = "decreasing"

            message = (
                f"{metric.replace('_', ' ').title()} is {direction} "
                f"(~{abs(slope_per_day):.2f}/run, R²={r_squared:.2f})"
            )

            trends.append(TrendAnalysis(
                metric=metric,
                direction=direction,
                slope_per_day=round(slope_per_day, 4),
                confidence=round(r_squared, 3),
                message=message,
            ))

        return trends

    async def _compute_plan_stability(
        self,
        pipeline_id: uuid.UUID,
        current_hash: str,
    ) -> str:
        """Determine plan stability by comparing the current plan hash against recent plans.

        Fetches the last 5 execution plan runs and computes their hashes. If
        all match, the plan is "stable". If some differ, it is "unstable".

        Args:
            pipeline_id: Pipeline UUID.
            current_hash: Hash of the plan being evaluated.

        Returns:
            "stable", "unstable", or "unknown" when insufficient data exists.
        """
        try:
            items, total = await self.resource_repo.get_execution_plan_runs(
                pipeline_id, skip=0, limit=5,
            )
        except (TypeError, ValueError):
            return "unknown"
        if total <= 1:
            return "unknown"

        # Fetch each plan and compute its hash
        hashes: set[str] = {current_hash}
        for item in items[:5]:
            run = await self.resource_repo.get_execution_plan_by_run(
                pipeline_id, item["dag_run_id"],
            )
            if run and run.execution_plan:
                try:
                    plan_data = json.loads(run.execution_plan)
                    hashes.add(self._compute_plan_hash(plan_data))
                except (json.JSONDecodeError, TypeError):
                    pass

        return "stable" if len(hashes) == 1 else "unstable"

    async def compare_execution_plans(
        self,
        pipeline_id: uuid.UUID,
        base_run_id: str,
        compare_run_id: str,
    ) -> PlanDiffResponse | None:
        """Fetch two execution plans and produce a structural diff.

        Compares the plan trees recursively: nodes with the same position are
        compared by name/type; changed nodes are flagged with ``status="changed"``;
        nodes present only in one plan are flagged ``"added"`` or ``"removed"``.

        Args:
            pipeline_id: Pipeline UUID (used for visibility scoping).
            base_run_id: DAG run ID for the baseline plan.
            compare_run_id: DAG run ID for the comparison plan.

        Returns:
            A :class:`PlanDiffResponse`, or ``None`` if either plan is missing.
        """
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        base_run = await self.resource_repo.get_execution_plan_by_run(pipeline_id, base_run_id)
        compare_run = await self.resource_repo.get_execution_plan_by_run(pipeline_id, compare_run_id)

        if not base_run or not compare_run:
            return None
        if not base_run.execution_plan or not compare_run.execution_plan:
            return None

        try:
            base_plan = json.loads(base_run.execution_plan)
            compare_plan = json.loads(compare_run.execution_plan)
        except (json.JSONDecodeError, TypeError):
            return None

        base_hash = self._compute_plan_hash(base_plan)
        compare_hash = self._compute_plan_hash(compare_plan)
        plan_changed = base_hash != compare_hash

        diff_node = self._diff_nodes(base_plan, compare_plan)

        changed_count = self._count_changed_nodes(diff_node)
        if plan_changed:
            summary = f"Plans differ: {changed_count} node(s) changed between runs."
        else:
            summary = "Plans are structurally identical."

        return PlanDiffResponse(
            base_run_id=base_run_id,
            compare_run_id=compare_run_id,
            plan_changed=plan_changed,
            diff=diff_node,
            summary=summary,
        )

    @staticmethod
    def _diff_nodes(base: dict, compare: dict) -> PlanDiffNode:
        """Recursively diff two plan node dicts and produce a PlanDiffNode tree.

        Args:
            base: Baseline plan node dict.
            compare: Comparison plan node dict.

        Returns:
            A populated :class:`PlanDiffNode` representing the diff.
        """
        base_name = base.get("name", "")
        compare_name = compare.get("name", "")
        base_type = base.get("type", "")
        compare_type = compare.get("type", "")

        name_changed = base_name != compare_name
        type_changed = base_type != compare_type
        metrics_changed = base.get("metrics", {}) != compare.get("metrics", {})

        if name_changed or type_changed:
            status = "changed"
        elif metrics_changed:
            status = "metrics_changed"
        else:
            status = "unchanged"

        # Diff children by position
        base_children = base.get("children", [])
        compare_children = compare.get("children", [])
        max_len = max(len(base_children), len(compare_children))

        diff_children: list[PlanDiffNode] = []
        for i in range(max_len):
            if i < len(base_children) and i < len(compare_children):
                diff_children.append(ResourceService._diff_nodes(base_children[i], compare_children[i]))
            elif i < len(base_children):
                diff_children.append(ResourceService._node_to_diff(base_children[i], "removed"))
            else:
                diff_children.append(ResourceService._node_to_diff(compare_children[i], "added"))

        return PlanDiffNode(
            name=compare_name or base_name,
            type=compare_type or base_type,
            status=status,
            metrics_before=base.get("metrics") or None,
            metrics_after=compare.get("metrics") or None,
            children=diff_children,
        )

    @staticmethod
    def _node_to_diff(node: dict, status: str) -> "PlanDiffNode":
        """Convert a single plan node dict to a PlanDiffNode with the given status."""
        children = [
            ResourceService._node_to_diff(c, status)
            for c in node.get("children", [])
        ]
        return PlanDiffNode(
            name=node.get("name", ""),
            type=node.get("type", ""),
            status=status,
            metrics_before=node.get("metrics") if status == "removed" else None,
            metrics_after=node.get("metrics") if status == "added" else None,
            children=children,
        )

    @staticmethod
    def _count_changed_nodes(node: "PlanDiffNode") -> int:
        """Count nodes with non-'unchanged' status in the diff tree."""
        count = 0 if node.status == "unchanged" else 1
        for child in node.children:
            count += ResourceService._count_changed_nodes(child)
        return count
