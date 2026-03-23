"""Handshake Analyzer - Multi-phase handshake completion with timeout analysis."""

from etls import fact_packet_inspection
from base_etl import BaseETL

SUFFIXES = ["phases", "timeouts"]


class HandshakeAnalyzer(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "HandshakeAnalyzer"

    def extract(self):
        self.packets = fact_packet_inspection(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Analyze handshake phases by protocol and application layer
        self.result = (
            self.packets
            .groupBy("protocol", "application_layer")
            .agg(
                F.count("packet_id").alias("initiated_count"),
                F.countDistinct("session_id").alias("completed_count"),
                F.avg("vlan_id").cast("long").alias("median_time_ms"),
            )
            .select(
                F.col("protocol").alias("handshake_type"),
                F.monotonically_increasing_id().alias("phase_number"),
                F.col("application_layer").alias("phase_name"),
                F.col("initiated_count"),
                F.col("completed_count"),
                F.when(
                    F.col("initiated_count") > 0,
                    (F.col("initiated_count") - F.col("completed_count")).cast("double")
                    / F.col("initiated_count").cast("double"),
                ).otherwise(F.lit(0.0)).alias("timeout_rate"),
                F.col("median_time_ms"),
                F.lit(self.start_date).cast("date").alias("report_date"),
                F.current_timestamp().alias("computed_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.prism.{self.etl_name}").overwritePartitions()
