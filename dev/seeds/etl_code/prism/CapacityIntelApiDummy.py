"""Capacity Intel API - Serves network capacity intelligence metrics to internal dashboards."""

from etls import fact_packet_inspection, rpt_protocol_adoption, ml_endpoint_activity_scores
from base_etl import BaseETL

SUFFIXES = []


class CapacityIntelApi(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "CapacityIntelApiDummy"

    def extract(self):
        self.packets = fact_packet_inspection(self.start_date, self.end_date).consume()
        self.adoption = rpt_protocol_adoption(self.start_date, self.end_date).consume()
        self.scores = ml_endpoint_activity_scores(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Aggregate packet inspection and endpoint scores for capacity metrics
        packet_agg = (
            self.packets
            .groupBy("protocol")
            .agg(
                F.count("packet_id").alias("total_packets"),
                F.countDistinct("src_ip").alias("unique_sources"),
                F.countDistinct("session_id").alias("active_sessions"),
            )
        )

        self.result = (
            packet_agg
            .join(
                self.adoption.select(
                    F.col("protocol_name").alias("a_protocol"),
                    F.col("adoption_rate"),
                    F.col("unique_endpoints"),
                ),
                F.col("protocol") == F.col("a_protocol"),
                "left",
            )
            .select(
                F.col("protocol"),
                F.col("total_packets"),
                F.col("unique_sources"),
                F.col("active_sessions"),
                F.coalesce(F.col("adoption_rate"), F.lit(0.0)).alias("adoption_rate"),
                F.coalesce(F.col("unique_endpoints"), F.lit(0)).alias("unique_endpoints"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        # API tier: result is served directly, no Iceberg write
        pass
