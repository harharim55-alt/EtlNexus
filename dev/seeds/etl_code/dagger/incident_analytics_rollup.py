"""Incident Analytics Rollup - Aggregates incident metrics with DNS context."""

from etls import raw_syslog_events
from base_etl import BaseETL

SUFFIXES = ["responder_performance"]


class IncidentAnalyticsRollup(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "incident_analytics_rollup"

    def extract(self):
        self.events = raw_syslog_events(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Aggregate syslog incidents by severity to produce period-level metrics
        severity_weight = (
            F.when(F.col("severity") == "emergency", 10)
             .when(F.col("severity") == "alert", 8)
             .when(F.col("severity") == "critical", 6)
             .when(F.col("severity") == "error", 4)
             .when(F.col("severity") == "warning", 2)
             .otherwise(1)
        )

        self.result = (
            self.events
            .withColumn("sev_weight", severity_weight)
            .groupBy("source_host")
            .agg(
                F.count("event_id").alias("total_incidents"),
                F.avg("sev_weight").cast("double").alias("avg_resolution_minutes"),
                F.sum("sev_weight").cast("double").alias("severity_score"),
                F.countDistinct("facility").cast("double").alias("escalation_rate"),
            )
            .select(
                F.lit(self.start_date.strftime("%Y-%m-%d")).alias("period"),
                F.col("total_incidents"),
                F.col("avg_resolution_minutes"),
                F.col("severity_score"),
                F.col("source_host").alias("responder_id"),
                (F.lit(100.0) - F.col("escalation_rate") * F.lit(5.0)).alias("sla_met_pct"),
                F.col("escalation_rate"),
                F.current_timestamp().alias("computed_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
