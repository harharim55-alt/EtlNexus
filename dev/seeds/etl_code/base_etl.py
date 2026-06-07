"""BaseETL — abstract base for all ETL classes in the cyber network analysis pipeline system.

All ETLs inherit from this class and implement extract(), transform(), load().
The SparkSession is shared or created with Iceberg catalog configuration.
EtlNexusMixin auto-instruments run() with structured log markers.
"""

import os
from datetime import timedelta

try:
    from etlnexus_hooks import EtlNexusMixin
except ImportError:
    EtlNexusMixin = None

_bases = (EtlNexusMixin,) if EtlNexusMixin is not None else ()


class BaseETL(*_bases):
    def __init__(self, start_date, end_date=None, schedule="daily"):
        self.start_date = start_date
        self.schedule = schedule
        if end_date:
            self.end_date = end_date
        elif schedule == "hourly":
            self.end_date = start_date + timedelta(hours=1)
        else:
            self.end_date = start_date + timedelta(days=1)
        self.spark = self._get_or_create_spark()
        self.hourkey = start_date.hour if schedule == "hourly" else None
        self.result = None

    def extract(self):
        raise NotImplementedError

    def transform(self):
        raise NotImplementedError

    def load(self):
        raise NotImplementedError

    @staticmethod
    def _get_or_create_spark():
        from pyspark.sql import SparkSession

        return (
            SparkSession.builder
            .appName("EtlNexus-ETL")
            .master("local[*]")
            .config("spark.jars", "/opt/airflow/jars/iceberg-spark-runtime.jar")
            .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
            .config("spark.sql.catalog.iceberg.type", "hadoop")
            .config("spark.sql.catalog.iceberg.warehouse", os.environ.get("SPARK_WAREHOUSE", "/tmp/warehouse"))
            .config(
                "spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
            )
            .config("spark.driver.memory", "512m")
            .config("spark.ui.enabled", "false")
            .getOrCreate()
        )
