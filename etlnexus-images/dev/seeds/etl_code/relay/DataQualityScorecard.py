"""Data Quality Scorecard — Final aggregation of all quality signals into a unified report.

Demonstrates: Multiple complex joins, Window with rank/dense_rank/lag,
complex Project expressions (CASE WHEN, cast chains, computed columns),
advanced Filter predicates (LIKE, IN, BETWEEN-style ranges).
"""

from etls import (
    schema_compliance_results,
    field_frequency_profiles,
    cross_team_audit_results,
    compliance_metrics_pivoted,
    anomaly_pattern_results,
)
from base_etl import BaseETL



class DataQualityScorecard(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "DataQualityScorecard"

    def extract(self):
        self.schema = schema_compliance_results(self.start_date, self.end_date).consume()
        self.profiles = field_frequency_profiles(self.start_date, self.end_date).consume()
        self.audit = cross_team_audit_results(self.start_date, self.end_date).consume()
        self.metrics = compliance_metrics_pivoted(self.start_date, self.end_date).consume()
        self.anomalies = anomaly_pattern_results(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window

        # Schema quality: ratio of matched fields
        schema_score = (
            self.schema
            .groupBy(F.lit(1).alias("key"))
            .agg(
                F.sum(F.when(F.col("status") == "matched", 1).otherwise(0)).alias("matched_count"),
                F.count("*").alias("total_fields"),
            )
            .withColumn("schema_score",
                        (F.col("matched_count").cast("double") / F.col("total_fields").cast("double") * 100))
        )

        # Audit quality per subnet
        audit_scores = (
            self.audit
            .groupBy("subnet_id")
            .agg(
                F.sum(F.when(F.col("audit_status") == "matched", 1).otherwise(0)).alias("matched_devices"),
                F.count("*").alias("total_devices"),
            )
            .withColumn("join_integrity_score",
                        F.col("matched_devices").cast("double") / F.col("total_devices").cast("double") * 100)
        )

        # Window: trend analysis with lag for day-over-day comparison
        w = Window.partitionBy("subnet_id").orderBy("computed_at")
        metrics_with_trend = (
            self.metrics
            .withColumn("prev_device_count", F.lag("device_count", 1).over(w))
            .withColumn("device_count_delta",
                        F.col("device_count") - F.coalesce(F.col("prev_device_count"), F.col("device_count")))
            .withColumn("trend_rank", F.dense_rank().over(
                Window.partitionBy("subnet_id").orderBy(F.col("device_count").desc())
            ))
        )

        # Join anomaly scores
        enriched = (
            audit_scores
            .join(self.anomalies, on="subnet_id", how="left")
        )

        # Complex Project: compute composite quality score with CASE expressions
        self.result = (
            enriched
            .withColumn("composite_score",
                F.when(F.col("pattern_label") == "high_anomaly",
                       F.col("join_integrity_score") * 0.5)
                .when(F.col("pattern_label") == "low_anomaly",
                      F.col("join_integrity_score") * 0.8)
                .otherwise(F.col("join_integrity_score"))
            )
            .withColumn("quality_tier",
                F.when(F.col("composite_score") >= 95, F.lit("platinum"))
                .when(F.col("composite_score") >= 80, F.lit("gold"))
                .when(F.col("composite_score") >= 60, F.lit("silver"))
                .otherwise(F.lit("bronze"))
            )
            .withColumn("alert_level",
                F.when(F.col("anomaly_count") > 10, F.lit("critical"))
                .when(F.col("anomaly_count") > 5, F.lit("warning"))
                .otherwise(F.lit("info"))
            )
            .select(
                "subnet_id",
                "join_integrity_score",
                F.coalesce("anomaly_count", F.lit(0)).alias("anomaly_count"),
                F.coalesce("pattern_label", F.lit("unknown")).alias("anomaly_pattern"),
                "composite_score",
                "quality_tier",
                "alert_level",
                F.current_timestamp().alias("scored_at"),
                F.lit(self.start_date).cast("date").alias("date"),
            )
        )

    def load(self):
        self.result.writeTo(f"iceberg.relay.{self.etl_name}").overwritePartitions()
