"""Peering ROI Calculator - Per-peer return on investment from attribution data."""

from etls import rpt_traffic_attribution
from base_etl import BaseETL

SUFFIXES = ["by_peer"]


class PeeringRoiCalculator(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "peering_roi_calculator"

    def extract(self):
        self.attribution = rpt_traffic_attribution(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Calculate ROI per peering interface from traffic attribution data
        self.result = (
            self.attribution
            .groupBy("interface")
            .agg(
                F.count("attribution_id").alias("total_flows"),
                F.sum("bandwidth_attributed_mbps").alias("total_bandwidth"),
                F.avg("attribution_weight").alias("avg_weight"),
                F.countDistinct("flow_id").alias("prefixes_exchanged"),
            )
            .select(
                F.concat_ws("-", F.lit("PEER"), F.col("interface")).alias("peer_id"),
                F.concat_ws("-", F.lit("Peer"), F.col("interface")).alias("peer_name"),
                F.col("interface"),
                # transit_cost: estimated based on bandwidth
                (F.col("total_bandwidth") * F.lit(0.10)).alias("transit_cost"),
                # bandwidth_value: value derived from total bandwidth with weight factor
                (F.col("total_bandwidth") * F.col("avg_weight")).alias("bandwidth_value"),
                # roi_pct
                F.when(
                    F.col("total_bandwidth") > 0,
                    ((F.col("total_bandwidth") * F.col("avg_weight")) - (F.col("total_bandwidth") * F.lit(0.10)))
                    / F.greatest(F.col("total_bandwidth") * F.lit(0.10), F.lit(1.0))
                    * F.lit(100.0),
                ).otherwise(F.lit(0.0)).alias("roi_pct"),
                F.col("prefixes_exchanged"),
                F.lit(self.start_date).cast("date").alias("report_date"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
