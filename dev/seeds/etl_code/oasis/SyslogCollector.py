"""Syslog Collector - Real-time streaming of network syslog events."""

from base_etl import BaseETL



class SyslogCollector(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="hourly")
        self.etl_name = "SyslogCollector"

    def extract(self):
        self.events = self.spark.table("iceberg.oasis.SyslogCollector")

    def transform(self):
        from pyspark.sql import functions as F

        # Filter events by severity (keep warning and above), assign priority ranking
        severity_order = F.when(F.col("severity") == "emergency", 0) \
            .when(F.col("severity") == "alert", 1) \
            .when(F.col("severity") == "critical", 2) \
            .when(F.col("severity") == "error", 3) \
            .when(F.col("severity") == "warning", 4) \
            .otherwise(5)

        self.result = (
            self.events
            .withColumn("_sev_rank", severity_order)
            .filter(F.col("_sev_rank") <= 4)
            .drop("_sev_rank")
            .select(
                F.col("event_id"),
                F.col("source_host"),
                F.col("facility"),
                F.col("severity"),
                F.col("message"),
                F.col("priority"),
                F.col("event_time"),
                F.col("received_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
            .withColumn("hourkey", F.lit(self.hourkey))
        )

    def load(self):
        self.result.writeTo(f"iceberg.oasis.{self.etl_name}").overwritePartitions()
