"""Traffic Class Segments - Behavioral traffic classification from usage patterns."""

from etls import fact_packet_inspection, ml_endpoint_activity_scores
from base_etl import BaseETL

SUFFIXES = ["transitions", "qos_profiles"]


class TrafficClassSegments(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "traffic_class_segments"

    def extract(self):
        self.packets = fact_packet_inspection(self.start_date, self.end_date).consume()
        self.scores = ml_endpoint_activity_scores(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Join packet inspection with activity scores to classify traffic
        packet_agg = (
            self.packets
            .groupBy("src_ip")
            .agg(
                F.count("packet_id").alias("flow_count_30d"),
                F.countDistinct("protocol").alias("protocols_used_30d"),
                F.max("capture_time").alias("last_active_at"),
            )
        )

        self.result = (
            packet_agg
            .join(
                self.scores.select(
                    F.col("endpoint_id").alias("score_endpoint"),
                    F.col("tier"),
                    F.col("activity_score"),
                ),
                F.col("src_ip") == F.col("score_endpoint"),
                "left",
            )
            .select(
                F.col("src_ip").alias("endpoint_id"),
                F.when(F.col("activity_score") > 5.0, F.lit("high-throughput"))
                 .when(F.col("activity_score") > 2.0, F.lit("standard"))
                 .when(F.col("activity_score") > 0.5, F.lit("low-volume"))
                 .otherwise(F.lit("idle")).alias("traffic_class"),
                F.coalesce(F.col("tier"), F.lit("unclassified")).alias("previous_class"),
                F.lit(1).cast("long").alias("days_in_class"),
                F.col("flow_count_30d"),
                F.col("protocols_used_30d"),
                F.col("last_active_at"),
                F.current_timestamp().alias("classified_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
