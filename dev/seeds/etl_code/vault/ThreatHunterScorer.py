"""Threat Hunter Scorer - ML-based threat qualification from DHCP lease data."""

from etls import stg_dhcp_leases, raw_syslog_events
from base_etl import BaseETL

SUFFIXES = ["indicators", "scores"]


class ThreatHunterScorer(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "ThreatHunterScorer"

    def extract(self):
        self.leases = stg_dhcp_leases(self.start_date, self.end_date).consume()
        self.events = raw_syslog_events(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Score threats by joining DHCP leases with syslog events per IP
        event_counts = (
            self.events
            .groupBy("source_host")
            .agg(
                F.count("event_id").alias("event_count"),
                F.sum(
                    F.when(F.col("severity").isin("emergency", "alert", "critical"), 1).otherwise(0)
                ).alias("critical_events"),
            )
        )

        self.result = (
            self.leases
            .join(
                event_counts,
                F.col("ip_address") == F.col("source_host"),
                "left",
            )
            .select(
                F.col("ip_address").alias("source_ip"),
                # threat_score: weighted combination of event severity
                (
                    F.coalesce(F.col("critical_events"), F.lit(0)).cast("double") * F.lit(10.0)
                    + F.coalesce(F.col("event_count"), F.lit(0)).cast("double") * F.lit(1.0)
                ).alias("threat_score"),
                F.when(F.coalesce(F.col("critical_events"), F.lit(0)) > 5, F.lit("critical"))
                 .when(F.coalesce(F.col("critical_events"), F.lit(0)) > 2, F.lit("high"))
                 .when(F.coalesce(F.col("event_count"), F.lit(0)) > 10, F.lit("medium"))
                 .otherwise(F.lit("low")).alias("risk_bucket"),
                (F.coalesce(F.col("event_count"), F.lit(0)).cast("double") / F.lit(100.0)).alias("anomaly_score"),
                (F.lit(1.0) - F.coalesce(F.col("critical_events"), F.lit(0)).cast("double") / F.greatest(F.coalesce(F.col("event_count"), F.lit(1)).cast("double"), F.lit(1.0))).alias("reputation_score"),
                F.coalesce(F.col("event_count"), F.lit(0)).alias("suspicious_connections"),
                (F.coalesce(F.col("critical_events"), F.lit(0)) > 5).alias("is_blocked"),
                F.current_timestamp().alias("scored_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.vault.{self.etl_name}").overwritePartitions()
