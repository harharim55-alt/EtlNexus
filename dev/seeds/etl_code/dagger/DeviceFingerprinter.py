"""Device Fingerprinter - Unified device profile from port, route, and DNS data."""

from etls import switch_interface_snapshot, stg_bgp_announcements, dns_zone_records
from base_etl import BaseETL



class DeviceFingerprinter(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "DeviceFingerprinter"

    def extract(self):
        self.ports = switch_interface_snapshot(self.start_date, self.end_date).consume()
        self.routes = stg_bgp_announcements(self.start_date, self.end_date).consume()
        self.dns = dns_zone_records(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Join switch ports with BGP routes on switch_id/peer_id, then with DNS on zone_name
        ports_routes = (
            self.ports
            .join(
                self.routes.select(
                    F.col("peer_id").alias("r_peer_id"),
                    F.col("prefix"),
                    F.col("as_path"),
                ),
                F.col("switch_id") == F.col("r_peer_id"),
                "left",
            )
        )

        dns_hosts = (
            self.dns
            .filter(F.col("record_type") == "A")
            .select(
                F.col("record_value").alias("dns_ip"),
                F.col("zone_name").alias("dns_hostname"),
            )
        )

        self.result = (
            ports_routes
            .join(dns_hosts, F.col("mac_address") == F.col("dns_ip"), "left")
            .select(
                F.concat_ws("-", F.lit("DEV"), F.col("switch_id").cast("string"), F.col("port_number")).alias("device_id"),
                F.col("mac_address"),
                F.coalesce(F.col("dns_hostname"), F.lit("unknown")).alias("hostname"),
                F.col("vlan_id").alias("open_ports"),
                F.coalesce(F.col("as_path"), F.lit("unknown")).alias("os_fingerprint"),
                F.when(F.col("port_speed") == "10Gbps", F.lit("server"))
                 .when(F.col("port_speed") == "1Gbps", F.lit("workstation"))
                 .otherwise(F.lit("iot")).alias("device_class"),
                F.col("port_number").alias("switch_port"),
                F.current_timestamp().alias("enriched_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
