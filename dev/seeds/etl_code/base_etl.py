"""BaseETL — abstract base for all ETL classes in the Dagger pipeline system.

All ETLs inherit from this class and implement extract(), transform(), load().
The SparkSession is shared or created with Iceberg catalog configuration.
"""

from datetime import timedelta


class BaseETL:
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

    def run(self):
        self.extract()
        self.transform()
        self.load()

    @staticmethod
    def _get_or_create_spark():
        from pyspark.sql import SparkSession

        return (
            SparkSession.builder
            .appName("EtlNexus-ETL")
            .master("local[*]")
            .config(
                "spark.jars.packages",
                "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.1",
            )
            .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
            .config("spark.sql.catalog.iceberg.type", "rest")
            .config("spark.sql.catalog.iceberg.uri", "http://iceberg-rest:8181")
            .config(
                "spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
            )
            .config("spark.driver.memory", "512m")
            .config("spark.ui.enabled", "false")
            .getOrCreate()
        )
