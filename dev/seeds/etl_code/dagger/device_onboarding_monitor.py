"""Device Onboarding Monitor - Onboarding phase completion and rejection analysis."""

from etls import fact_packet_inspection
from base_etl import BaseETL

SUFFIXES = ["phases", "batches"]


class DeviceOnboardingMonitor(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "device_onboarding_monitor"

    def extract(self):
        self.packets = fact_packet_inspection(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Track device onboarding funnel by application layer as proxy for onboarding phases
        total_devices = self.packets.select("src_ip").distinct().count()
        total_devices_lit = F.lit(max(total_devices, 1))

        self.result = (
            self.packets
            .groupBy("application_layer")
            .agg(
                F.countDistinct("src_ip").alias("devices_reached"),
                F.avg("vlan_id").cast("long").alias("median_provision_time_sec"),
                F.count("packet_id").alias("total_packets"),
            )
            .select(
                F.lit(self.start_date).cast("date").alias("batch_date"),
                F.col("application_layer").alias("phase_name"),
                F.monotonically_increasing_id().alias("phase_order"),
                F.col("devices_reached"),
                (F.col("devices_reached").cast("double") / total_devices_lit).alias("completion_rate"),
                F.col("median_provision_time_sec"),
                (F.lit(1.0) - F.col("devices_reached").cast("double") / total_devices_lit).alias("rejection_rate"),
                F.current_timestamp().alias("computed_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
