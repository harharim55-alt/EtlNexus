"""Deep Packet Inspector - Enriches raw flow data with device context."""

from etls import fact_netflow_records, switch_interface_snapshot
from base_etl import BaseETL



class DeepPacketInspector(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "DeepPacketInspector"

    def extract(self):
        self.flows = fact_netflow_records(self.start_date, self.end_date).consume()
        self.ports = switch_interface_snapshot(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Join netflow records with switch port data to enrich packets with port context
        port_info = (
            self.ports
            .select(
                F.col("mac_address").alias("port_mac"),
                F.col("port_speed"),
                F.col("vlan_id"),
                F.col("collected_at").alias("port_collected_at"),
            )
            .dropDuplicates(["port_mac"])
        )

        self.result = (
            self.flows
            .join(port_info, F.col("src_ip") == F.col("port_mac"), "left")
            .select(
                F.concat_ws("-", F.lit("PKT"), F.col("flow_id")).alias("packet_id"),
                F.col("src_ip"),
                F.col("protocol"),
                F.col("capture_time"),
                F.col("session_id"),
                F.when(F.col("protocol") == "TCP", F.lit("HTTP"))
                 .when(F.col("protocol") == "UDP", F.lit("DNS"))
                 .otherwise(F.lit("UNKNOWN")).alias("application_layer"),
                F.coalesce(F.col("port_speed"), F.lit("unknown")).alias("port_speed"),
                F.coalesce(F.col("vlan_id"), F.lit(0)).alias("vlan_id"),
                F.col("capture_time").cast("date").alias("first_seen_date"),
                F.current_timestamp().alias("enriched_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.prism.{self.etl_name}").overwritePartitions()
