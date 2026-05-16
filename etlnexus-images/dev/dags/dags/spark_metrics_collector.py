"""Backward-compat re-export — collector now lives in etlnexus_hooks package."""

from etlnexus_hooks.metrics_collector import SparkMetricsCollector, collect_spark_metrics

__all__ = ["SparkMetricsCollector", "collect_spark_metrics"]
