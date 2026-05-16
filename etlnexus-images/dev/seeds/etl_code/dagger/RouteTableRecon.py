"""Route Table Recon - Daily synchronization of transit routing tables."""

from etls import switch_interface_snapshot
from base_etl import BaseETL



class RouteTableRecon(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "RouteTableRecon"

    def extract(self):
        self.ports = switch_interface_snapshot(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Enrich BGP routes from switch port data: derive route entries per active port
        self.result = (
            self.ports
            .filter(F.col("is_active") == True)
            .groupBy("switch_id", "vlan_id")
            .agg(
                F.count("port_number").alias("prefix_count"),
                F.first("mac_address").alias("next_hop_mac"),
                F.max("collected_at").alias("synced_at"),
            )
            .select(
                F.monotonically_increasing_id().alias("route_id"),
                F.concat_ws("/", F.col("switch_id").cast("string"), F.col("vlan_id").cast("string")).alias("prefix"),
                F.col("next_hop_mac").alias("next_hop"),
                F.concat_ws(" ", F.lit("AS"), F.col("switch_id").cast("string")).alias("as_path"),
                F.lit("igp").alias("origin"),
                F.lit("active").alias("status"),
                F.col("switch_id").alias("peer_id"),
                F.col("synced_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
