"""Shared ETL runner — executes ETL tasks via BaseETL subclasses with EtlNexusMixin.

All ETLs inherit from BaseETL which includes EtlNexusMixin. The mixin's run()
auto-emits all structured log markers (ETL_DESCRIPTION, ETL_WRITES_TO,
ETL_RESOURCE_ACTUAL, ETL_EXECUTION_PLAN). This runner's job is simply:
find the ETL class, create a SparkSession, and run it.
"""

import importlib
import json
import logging
import random
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

ETL_CODE_ROOT = Path("/data/etl-code")


def _find_etl_file(etl_name: str) -> Path:
    """Search team subdirectories for an ETL code file."""
    for team_dir in sorted(ETL_CODE_ROOT.iterdir()):
        if team_dir.is_dir() and not team_dir.name.startswith((".", "__")):
            candidate = team_dir / f"{etl_name}.py"
            if candidate.exists():
                return candidate
    return ETL_CODE_ROOT / f"dagger/{etl_name}.py"  # fallback


def run_etl(etl_name, spark_callable=None, **kwargs):
    """Execute an ETL task with real Spark via BaseETL + EtlNexusMixin.

    Args:
        etl_name: Name of the ETL task (PascalCase).
        spark_callable: Optional function(spark, **kwargs) for custom Spark work.
            If None, the ETL class is auto-discovered from team directories.
        **kwargs: Airflow op_kwargs (resources, ti, etc.)
    """
    print(f"ETL_START: {etl_name}")

    # Test failure injection (keeps failure scenario testing in threat_detection DAG)
    simulate_failure = kwargs.get("simulate_failure")
    if simulate_failure:
        raise RuntimeError(simulate_failure)
    simulate_flaky = kwargs.get("simulate_flaky")
    if simulate_flaky and random.random() < 0.4:
        raise RuntimeError(simulate_flaky)

    # Auto-create callable from ETL class if not provided
    if spark_callable is None:
        spark_callable = _make_etl_callable(etl_name, kwargs.get("ti"))

    if spark_callable is None:
        logger.warning("No ETL class or spark_callable for %s — skipping", etl_name)
        return

    # Resolve resource config and run with real Spark
    effective_cfg = _resolve_resources(kwargs)
    _run_real_spark(etl_name, spark_callable, effective_cfg, kwargs)


def _resolve_resources(kwargs: dict) -> dict:
    """Resolve effective Spark resource config (default + DAG override)."""
    resources = kwargs.get("resources")
    if not resources:
        return {}
    dag_id = ""
    ti = kwargs.get("ti")
    if ti:
        dag_id = getattr(ti, "dag_id", "")
    default_cfg = resources.get("default", {})
    dag_override = resources.get(dag_id, {}) if dag_id else {}
    return {**default_cfg, **dag_override}


def _make_etl_callable(etl_name: str, ti=None):
    """Create a spark_callable from an ETL class file.

    Dynamically imports the ETL module, finds the BaseETL subclass,
    and returns a callable that instantiates and runs the ETL.
    The mixin on BaseETL handles all marker emission during run().
    """
    from datetime import datetime

    if ti and hasattr(ti, "execution_date") and ti.execution_date:
        start_date = ti.execution_date
    else:
        start_date = datetime(2026, 3, 10)

    etl_code_path = "/data/etl-code"
    if etl_code_path not in sys.path:
        sys.path.insert(0, etl_code_path)

    # Search team subdirectories for the ETL module
    mod = None
    for team_dir in sorted(ETL_CODE_ROOT.iterdir()):
        if team_dir.is_dir() and not team_dir.name.startswith((".", "__")):
            try:
                mod = importlib.import_module(f"{team_dir.name}.{etl_name}")
                break
            except ImportError:
                continue
    if mod is None:
        logger.warning("Could not import ETL module %s from any team directory", etl_name)
        return None

    # Find the ETL class (has extract/transform/load methods)
    etl_class = None
    for obj in vars(mod).values():
        if (
            isinstance(obj, type)
            and hasattr(obj, "extract")
            and hasattr(obj, "transform")
            and hasattr(obj, "load")
            and obj.__name__ != "BaseETL"
        ):
            etl_class = obj
            break

    if etl_class is None:
        logger.warning("No ETL class found for %s", etl_name)
        return None

    def callable(spark, **kwargs):
        etl = etl_class(start_date)
        etl.spark = spark
        etl.run()  # Mixin wraps this: emits all markers automatically

    return callable


def _run_real_spark(
    etl_name: str, spark_callable, config: dict, kwargs: dict
) -> None:
    """Create a SparkSession, run the callable, and collect metrics via sparkMeasure."""
    spark = _create_spark_session(etl_name, config)
    try:
        try:
            from spark_metrics_collector import collect_spark_metrics
            with collect_spark_metrics(spark) as collector:
                spark_callable(spark, **kwargs)
        except Exception as metrics_err:
            logger.warning(
                "sparkMeasure unavailable for %s (%s), running without metrics",
                etl_name, type(metrics_err).__name__,
            )
            spark_callable(spark, **kwargs)
    except Exception:
        logger.exception("Spark task %s failed", etl_name)
        raise
    finally:
        spark.stop()


def _create_spark_session(etl_name: str, config: dict):
    """Create a SparkSession configured from the resource allocation dict."""
    from pyspark.sql import SparkSession

    builder = SparkSession.builder.appName(etl_name)

    if config.get("spark_driver_memory"):
        builder = builder.config("spark.driver.memory", config["spark_driver_memory"])
    if config.get("spark_executor_memory"):
        builder = builder.config("spark.executor.memory", config["spark_executor_memory"])
    if config.get("spark_executor_cores"):
        builder = builder.config("spark.executor.cores", str(config["spark_executor_cores"]))
    if config.get("spark_num_executors"):
        builder = builder.config("spark.executor.instances", str(config["spark_num_executors"]))

    builder = builder.config(
        "spark.jars",
        "/opt/airflow/jars/iceberg-spark-runtime.jar,"
        "/opt/airflow/jars/spark-measure.jar",
    )
    builder = builder.config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
    builder = builder.config("spark.sql.catalog.iceberg.type", "rest")
    builder = builder.config("spark.sql.catalog.iceberg.uri", "http://iceberg-rest:8181")
    builder = builder.config(
        "spark.sql.extensions",
        "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    )
    builder = builder.config("spark.eventLog.enabled", "true")
    builder = builder.config("spark.eventLog.dir", "/tmp/spark-events")
    builder = builder.master("local[*]")

    return builder.getOrCreate()
