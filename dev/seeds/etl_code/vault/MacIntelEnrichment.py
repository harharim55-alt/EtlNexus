"""MAC Intel Enrichment - Enriches MAC addresses with DHCP and HTTP access data."""

from etls import stg_dhcp_leases, stg_http_access_logs
from base_etl import BaseETL

SUFFIXES = ["vendor_lookups"]


class MacIntelEnrichment(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "MacIntelEnrichment"

    def extract(self):
        self.leases = stg_dhcp_leases(self.start_date, self.end_date).consume()
        self.logs = stg_http_access_logs(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Aggregate HTTP log activity per client IP
        log_stats = (
            self.logs
            .groupBy("client_ip")
            .agg(
                F.count("request_id").alias("total_flows"),
                F.countDistinct("request_path").alias("unique_destinations"),
                F.first("user_agent").alias("last_user_agent"),
            )
        )

        # Join DHCP leases with HTTP log stats on IP address
        self.result = (
            self.leases
            .join(log_stats, F.col("ip_address") == F.col("client_ip"), "left")
            .select(
                F.col("mac_address"),
                F.col("ip_address"),
                F.coalesce(F.col("total_flows"), F.lit(0)).alias("total_flows"),
                F.coalesce(F.col("unique_destinations"), F.lit(0)).alias("unique_destinations"),
                F.col("pool_name").alias("last_seen_interface"),
                # Derive vendor from MAC OUI prefix
                F.when(F.col("mac_address").startswith("00:1A"), F.lit("Cisco"))
                 .when(F.col("mac_address").startswith("00:50"), F.lit("VMware"))
                 .when(F.col("mac_address").startswith("AC:DE"), F.lit("Dell"))
                 .otherwise(F.lit("Unknown")).alias("vendor_name"),
                F.lit(0).cast("long").alias("days_since_last_seen"),
                F.current_timestamp().alias("enriched_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.vault.{self.etl_name}").overwritePartitions()
