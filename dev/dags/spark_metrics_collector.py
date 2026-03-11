"""Spark metrics collector — captures real PySpark resource usage via sparkMeasure.

Provides a context manager that wraps SparkSession execution and extracts
granular metrics (CPU time, GC, shuffle, I/O, memory spill, etc.) from
Spark's internal listener infrastructure.

Falls back to basic SparkContext metrics if sparkMeasure is not installed.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from sparkmeasure import StageMetrics

    _HAS_SPARKMEASURE = True
except ImportError:
    _HAS_SPARKMEASURE = False


class SparkMetricsCollector:
    """Collects Spark execution metrics around a SparkSession workload.

    Usage::

        collector = SparkMetricsCollector(spark)
        collector.begin()
        # ... run Spark workload ...
        collector.end()
        metrics = collector.get_metrics()
    """

    def __init__(self, spark):
        self.spark = spark
        self._stage_metrics = None
        self._metrics = {}

    def begin(self):
        if _HAS_SPARKMEASURE:
            self._stage_metrics = StageMetrics(self.spark)
            self._stage_metrics.begin()
        return self

    def end(self):
        if self._stage_metrics is not None:
            self._stage_metrics.end()
            self._metrics = self._extract_sparkmeasure_metrics()
        else:
            self._metrics = self._extract_basic_metrics()

    def get_metrics(self) -> dict:
        """Return collected metrics dict matching pipeline_run_history columns."""
        return self._metrics

    def _extract_sparkmeasure_metrics(self) -> dict:
        """Extract metrics from sparkMeasure's aggregate stage data."""
        try:
            agg = self._stage_metrics.aggregate_stagemetrics()
        except Exception:
            logger.warning("sparkMeasure aggregate failed, falling back to basic metrics")
            return self._extract_basic_metrics()

        executor_run_time = agg.get("executorRunTime", 0)
        executor_cpu_time = agg.get("executorCpuTime", 0)

        # Derive the 4 original fields for backward compatibility
        driver_mem_mb = self._get_driver_memory_mb()
        executors_active = self._get_executor_count()
        cpu_pct = (
            round((executor_cpu_time / executor_run_time) * 100, 1)
            if executor_run_time > 0
            else 0.0
        )
        peak_exec_mem = agg.get("peakExecutionMemory", 0)
        executor_mem_peak_mb = round(peak_exec_mem / (1024 * 1024)) if peak_exec_mem else None

        return {
            # Original 4 fields (backward compat)
            "driver_memory_used_mb": driver_mem_mb,
            "executor_memory_peak_mb": executor_mem_peak_mb,
            "cpu_utilization_pct": cpu_pct,
            "executors_active": executors_active,
            # sparkMeasure extended metrics
            "spark_application_id": self.spark.sparkContext.applicationId,
            "executor_run_time_ms": executor_run_time,
            "executor_cpu_time_ms": executor_cpu_time,
            "jvm_gc_time_ms": agg.get("jvmGCTime", 0),
            "shuffle_read_bytes": agg.get("shuffleTotalBytesRead", 0),
            "shuffle_write_bytes": agg.get("shuffleTotalBytesWritten", 0),
            "input_bytes": agg.get("bytesRead", 0),
            "output_bytes": agg.get("bytesWritten", 0),
            "memory_bytes_spilled": agg.get("memoryBytesSpilled", 0),
            "disk_bytes_spilled": agg.get("diskBytesSpilled", 0),
            "peak_execution_memory": peak_exec_mem,
            "result_size_bytes": agg.get("resultSize", 0),
            "num_tasks": agg.get("numTasks", 0),
            "num_stages": agg.get("numStages", 0),
            "metrics_source": "sparkmeasure",
        }

    def _extract_basic_metrics(self) -> dict:
        """Fallback: extract what's available from SparkContext directly."""
        driver_mem_mb = self._get_driver_memory_mb()
        executors_active = self._get_executor_count()

        return {
            "driver_memory_used_mb": driver_mem_mb,
            "executor_memory_peak_mb": None,
            "cpu_utilization_pct": None,
            "executors_active": executors_active,
            "spark_application_id": self.spark.sparkContext.applicationId,
            "metrics_source": "sparkcontext",
        }

    def _get_driver_memory_mb(self) -> int | None:
        """Get driver memory usage from JVM executor memory status."""
        try:
            sc = self.spark.sparkContext
            # getExecutorMemoryStatus returns Map[String, (Long, Long)]
            # where key is host:port, value is (maxMem, remainingMem)
            mem_status = sc._jsc.sc().getExecutorMemoryStatus()
            # The driver entry key contains "driver" or is the first entry
            for entry in mem_status.entrySet().toArray():
                max_mem = entry.getValue()._1()
                remaining = entry.getValue()._2()
                used_bytes = max_mem - remaining
                return round(used_bytes / (1024 * 1024))
        except Exception:
            logger.debug("Could not read driver memory from SparkContext")
        return None

    def _get_executor_count(self) -> int:
        """Get count of active executors (excluding driver)."""
        try:
            sc = self.spark.sparkContext
            # statusTracker gives executor info
            executors = sc._jsc.sc().getExecutorMemoryStatus().size()
            return max(executors - 1, 0)  # exclude driver
        except Exception:
            return 0


class _CollectorContextManager:
    """Context manager wrapper for SparkMetricsCollector."""

    def __init__(self, spark):
        self._collector = SparkMetricsCollector(spark)

    def __enter__(self):
        self._collector.begin()
        return self._collector

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._collector.end()
        return False


def collect_spark_metrics(spark):
    """Context manager that collects Spark metrics during execution.

    Usage::

        with collect_spark_metrics(spark) as collector:
            spark.sql("SELECT ...").write.parquet("/output")
        metrics = collector.get_metrics()
    """
    return _CollectorContextManager(spark)
