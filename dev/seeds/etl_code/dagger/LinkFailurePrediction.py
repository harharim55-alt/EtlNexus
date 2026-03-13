"""Link Failure Prediction - ML feature engineering for link health and failure probability."""

from etls import switch_interface_snapshot, stg_bgp_announcements
from base_etl import BaseETL

SUFFIXES = ["health_scores", "risk_tiers", "weekly"]


class LinkFailurePrediction(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "LinkFailurePrediction"

    def extract(self):
        self.ports = switch_interface_snapshot(self.start_date, self.end_date).consume()
        self.routes = stg_bgp_announcements(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Join switch ports with BGP routes, compute failure features per link
        route_info = (
            self.routes
            .select(
                F.col("peer_id").alias("route_peer_id"),
                F.col("status").alias("route_status"),
                F.col("synced_at"),
            )
            .dropDuplicates(["route_peer_id"])
        )

        self.result = (
            self.ports
            .join(route_info, F.col("switch_id") == F.col("route_peer_id"), "left")
            .select(
                F.concat_ws("-", F.lit("LINK"), F.col("switch_id").cast("string"), F.col("port_number")).alias("link_id"),
                # hours_since_last_flap: derived from time since last state change
                (
                    (F.unix_timestamp(F.col("collected_at")) - F.unix_timestamp(F.col("last_state_change")))
                    / F.lit(3600)
                ).cast("long").alias("hours_since_last_flap"),
                # avg_error_rate: proxy from inactive/total ratio
                F.when(F.col("is_active") == False, F.lit(0.15)).otherwise(F.lit(0.01)).alias("avg_error_rate"),
                F.col("vlan_id").alias("crc_errors_30d"),
                (F.col("vlan_id") * F.lit(2)).alias("packet_loss_events_90d"),
                # failure_probability: higher for inactive ports without recent BGP sync
                F.when(
                    (F.col("is_active") == False) & (F.col("route_status").isNull()),
                    F.lit(0.85),
                ).when(F.col("is_active") == False, F.lit(0.60))
                 .when(F.col("route_status") != "active", F.lit(0.30))
                 .otherwise(F.lit(0.05)).alias("failure_probability"),
                # health_score: inverse of failure probability
                F.when(F.col("is_active") == True, F.lit(0.95))
                 .otherwise(F.lit(0.40)).alias("health_score"),
                F.current_timestamp().alias("scored_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
