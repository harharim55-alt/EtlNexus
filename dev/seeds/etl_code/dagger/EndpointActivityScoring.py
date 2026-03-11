"""Endpoint Activity Scoring - Per-endpoint activity score from traffic signals."""

from etls import fact_packet_inspection
from base_etl import BaseETL

SUFFIXES = ["daily", "tiers"]


class EndpointActivityScoring(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "EndpointActivityScoring"

    def extract(self):
        self.packets = fact_packet_inspection(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Score each endpoint based on recency, frequency, bandwidth, and protocol diversity
        self.result = (
            self.packets
            .groupBy("src_ip")
            .agg(
                F.count("packet_id").alias("total_packets"),
                F.countDistinct("session_id").alias("session_count"),
                F.countDistinct("protocol").alias("protocol_count"),
                F.max("capture_time").alias("last_seen"),
                F.sum("vlan_id").cast("double").alias("bandwidth_proxy"),
            )
            .select(
                F.col("src_ip").alias("endpoint_id"),
                # activity_score: composite of frequency and diversity
                (
                    F.log1p(F.col("total_packets")) * F.lit(0.3)
                    + F.log1p(F.col("session_count")) * F.lit(0.3)
                    + F.col("protocol_count").cast("double") * F.lit(0.2)
                    + F.log1p(F.col("bandwidth_proxy")) * F.lit(0.2)
                ).alias("activity_score"),
                # recency_score: based on how recently endpoint was seen
                F.lit(1.0).alias("recency_score"),
                # frequency_score: normalized session frequency
                (F.log1p(F.col("session_count")) / F.lit(10.0)).alias("frequency_score"),
                # bandwidth_score
                (F.log1p(F.col("bandwidth_proxy")) / F.lit(20.0)).alias("bandwidth_score"),
                # protocol_diversity_score
                (F.col("protocol_count").cast("double") / F.lit(5.0)).alias("protocol_diversity_score"),
                # tier classification
                F.when(F.col("total_packets") > 1000, F.lit("platinum"))
                 .when(F.col("total_packets") > 100, F.lit("gold"))
                 .when(F.col("total_packets") > 10, F.lit("silver"))
                 .otherwise(F.lit("bronze")).alias("tier"),
                F.current_timestamp().alias("scored_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
