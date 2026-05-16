"""Capacity Threat Forecast - Network capacity forecast combining threat scores and attribution."""

from etls import ml_threat_scores, rpt_traffic_attribution
from base_etl import BaseETL



class CapacityThreatForecast(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "CapacityThreatForecast"

    def extract(self):
        self.threats = ml_threat_scores(self.start_date, self.end_date).consume()
        self.attribution = rpt_traffic_attribution(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Aggregate threat and attribution data to produce capacity forecasts per interface
        threat_agg = (
            self.threats
            .groupBy(F.lit("all").alias("_key"))
            .agg(
                F.avg("threat_score").alias("avg_threat"),
                F.sum(F.when(F.col("is_blocked"), 1).otherwise(0)).alias("blocked_count"),
                F.count("source_ip").alias("total_ips"),
            )
        )

        attr_agg = (
            self.attribution
            .groupBy(F.lit("all").alias("_key"))
            .agg(
                F.sum("bandwidth_attributed_mbps").alias("total_bandwidth"),
                F.countDistinct("interface").alias("link_count"),
                F.count("attribution_id").alias("total_attributions"),
            )
        )

        self.result = (
            threat_agg
            .join(attr_agg, "_key")
            .select(
                F.concat_ws("-", F.lit("FC"), F.lit(self.start_date.strftime("%Y%m%d"))).alias("forecast_id"),
                F.lit(self.start_date.strftime("%Y-%m")).alias("period"),
                # current utilization: proxy from bandwidth vs capacity
                F.least(
                    (F.col("total_bandwidth") / F.greatest(F.col("link_count") * F.lit(1000.0), F.lit(1.0))) * F.lit(100.0),
                    F.lit(100.0),
                ).alias("current_utilization_pct"),
                # projected utilization: current + threat-driven growth
                F.least(
                    (F.col("total_bandwidth") / F.greatest(F.col("link_count") * F.lit(1000.0), F.lit(1.0))) * F.lit(100.0)
                    + (F.col("avg_threat") * F.lit(2.0)),
                    F.lit(100.0),
                ).alias("projected_utilization_pct"),
                # saturation probability based on blocked IPs ratio
                (F.col("blocked_count").cast("double") / F.greatest(F.col("total_ips").cast("double"), F.lit(1.0))).alias("saturation_probability"),
                F.col("link_count").alias("links_at_risk"),
                # recommended upgrade based on projected growth
                (F.col("total_bandwidth") * F.lit(0.20) / F.lit(1000.0)).alias("recommended_upgrade_gbps"),
                F.lit(self.start_date).cast("date").alias("forecast_date"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.vault.{self.etl_name}").overwritePartitions()
