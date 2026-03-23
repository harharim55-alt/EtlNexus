"""Protocol Analyzer - Per-protocol adoption rates and version curves."""

from etls import fact_packet_inspection
from base_etl import BaseETL

SUFFIXES = ["daily", "weekly", "by_version"]


class ProtocolAnalyzer(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "ProtocolAnalyzer"

    def extract(self):
        self.packets = fact_packet_inspection(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Compute per-protocol adoption stats from packet inspection data
        total_endpoints = self.packets.select("src_ip").distinct().count()
        total_endpoints_lit = F.lit(max(total_endpoints, 1))

        self.result = (
            self.packets
            .groupBy("protocol")
            .agg(
                F.countDistinct("src_ip").alias("unique_endpoints"),
                F.countDistinct(
                    F.when(F.col("first_seen_date") == F.lit(self.start_date).cast("date"), F.col("src_ip"))
                ).alias("first_seen_count"),
                F.countDistinct("session_id").alias("daily_active"),
                F.countDistinct("src_ip").alias("weekly_active"),
            )
            .select(
                F.col("protocol").alias("protocol_name"),
                F.lit(self.start_date).cast("date").alias("report_date"),
                F.col("unique_endpoints"),
                F.col("first_seen_count"),
                F.col("daily_active"),
                F.col("weekly_active"),
                (F.col("unique_endpoints").cast("double") / total_endpoints_lit).alias("adoption_rate"),
                F.current_timestamp().alias("computed_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.prism.{self.etl_name}").overwritePartitions()
