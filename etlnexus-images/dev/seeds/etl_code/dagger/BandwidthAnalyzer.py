"""Bandwidth Analyzer - Aggregates bandwidth metering and circuit billing events."""

from etls import switch_interface_snapshot
from base_etl import BaseETL


class BandwidthAnalyzer(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "BandwidthAnalyzer"

    def extract(self):
        self.ports = switch_interface_snapshot(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Aggregate bandwidth by circuit (switch_id + vlan_id)
        self.result = (
            self.ports
            .groupBy("switch_id", "vlan_id")
            .agg(
                F.count("port_number").alias("port_count"),
                F.sum(F.when(F.col("is_active"), 1).otherwise(0)).alias("active_ports"),
                F.max("collected_at").alias("last_collection"),
            )
            .select(
                F.concat_ws("-", F.lit("INV"), F.col("switch_id").cast("string"), F.col("vlan_id").cast("string")).alias("invoice_id"),
                F.concat_ws("-", F.lit("CKT"), F.col("switch_id").cast("string")).alias("circuit_id"),
                F.concat_ws("-", F.lit("SUB"), F.col("vlan_id").cast("string")).alias("subscription_id"),
                (F.col("port_count") * F.lit(100.0)).alias("bandwidth_allocated_mbps"),
                (F.col("active_ports") * F.lit(85.0)).alias("bandwidth_used_mbps"),
                F.when(F.col("active_ports") > 5, F.lit("premium"))
                 .when(F.col("active_ports") > 2, F.lit("standard"))
                 .otherwise(F.lit("basic")).alias("billing_tier"),
                F.lit("invoiced").alias("status"),
                F.lit(self.start_date).cast("timestamp").alias("period_start"),
                F.lit(self.end_date).cast("timestamp").alias("period_end"),
                F.current_timestamp().alias("created_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

        # Tier summary — aggregate billing totals per tier
        self.tier_summary = (
            self.result
            .groupBy("billing_tier")
            .agg(
                F.count("*").alias("circuit_count"),
                F.sum("bandwidth_allocated_mbps").alias("total_allocated_mbps"),
                F.sum("bandwidth_used_mbps").alias("total_used_mbps"),
            )
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
        self.tier_summary.writeTo(f"iceberg.dagger.{self.etl_name}_tier_summary").overwritePartitions()
