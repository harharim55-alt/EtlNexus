"""Weekly Network Digest - Executive summary of network operations and peering performance."""

from etls import rpt_peering_roi, rpt_capacity_forecast, dim_enriched_mac_addresses, fact_cdn_costs
from base_etl import BaseETL

SUFFIXES = ["highlights"]


class WeeklyNetworkDigest(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "weekly_network_digest"

    def extract(self):
        self.roi = rpt_peering_roi(self.start_date, self.end_date).consume()
        self.forecast = rpt_capacity_forecast(self.start_date, self.end_date).consume()
        self.macs = dim_enriched_mac_addresses(self.start_date, self.end_date).consume()
        self.cdn = fact_cdn_costs(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Aggregate across all sources to produce a weekly digest
        roi_agg = (
            self.roi
            .agg(
                F.sum("bandwidth_value").alias("total_bandwidth_value"),
                F.count("peer_id").alias("peer_count"),
            )
        )

        forecast_agg = (
            self.forecast
            .agg(
                F.avg("current_utilization_pct").alias("avg_utilization"),
            )
        )

        mac_agg = (
            self.macs
            .agg(
                F.countDistinct("mac_address").alias("new_endpoints"),
            )
        )

        cdn_agg = (
            self.cdn
            .agg(
                F.sum("reported_bandwidth_gb").alias("total_cdn_bw"),
                F.sum("requests_total").alias("total_requests"),
            )
        )

        self.result = (
            roi_agg.crossJoin(forecast_agg).crossJoin(mac_agg).crossJoin(cdn_agg)
            .select(
                F.concat_ws("-", F.lit("DIG"), F.lit(self.start_date.strftime("%Y%m%d"))).alias("digest_id"),
                F.lit(self.start_date).cast("date").alias("week_start"),
                (F.coalesce(F.col("total_cdn_bw"), F.lit(0.0)) / F.lit(1024.0)).alias("total_bandwidth_tb"),
                F.col("peer_count").alias("total_incidents"),
                F.least(
                    F.lit(100.0) - F.coalesce(F.col("avg_utilization"), F.lit(0.0)),
                    F.lit(99.99),
                ).alias("uptime_pct"),
                F.lit("TCP").alias("top_protocol"),
                F.coalesce(F.col("new_endpoints"), F.lit(0)).alias("new_endpoints"),
                F.current_timestamp().alias("generated_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
