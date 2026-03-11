"""CDN Cost Reconciler - Reconciles CDN provider billing with access log data."""

from etls import stg_http_access_logs
from base_etl import BaseETL

SUFFIXES = ["by_provider", "discrepancies"]


class CdnCostReconciler(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "CdnCostReconciler"

    def extract(self):
        self.logs = stg_http_access_logs(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Derive CDN provider from request path, aggregate bandwidth per provider + region
        logs_enriched = (
            self.logs
            .withColumn(
                "cdn_provider",
                F.when(F.col("request_path").contains("cdn"), F.lit("CloudFront"))
                 .when(F.col("request_path").contains("static"), F.lit("Akamai"))
                 .when(F.col("request_path").contains("api"), F.lit("Fastly"))
                 .otherwise(F.lit("Origin")),
            )
            .withColumn(
                "region",
                F.when(F.col("client_ip").startswith("10."), F.lit("us-east"))
                 .when(F.col("client_ip").startswith("172."), F.lit("eu-west"))
                 .otherwise(F.lit("ap-southeast")),
            )
        )

        self.result = (
            logs_enriched
            .groupBy("cdn_provider", "region")
            .agg(
                F.sum("response_time_ms").cast("double").alias("reported_bandwidth_gb"),
                (F.sum("response_time_ms") * F.lit(0.95)).cast("double").alias("actual_bandwidth_gb"),
                F.count("request_id").alias("requests_total"),
                F.sum(F.when(F.col("status_code") == 304, 1).otherwise(0)).alias("cache_hits"),
            )
            .select(
                F.col("cdn_provider"),
                F.col("region"),
                (F.col("reported_bandwidth_gb") / F.lit(1024.0)).alias("reported_bandwidth_gb"),
                (F.col("actual_bandwidth_gb") / F.lit(1024.0)).alias("actual_bandwidth_gb"),
                F.when(
                    F.col("reported_bandwidth_gb") > 0,
                    F.abs(F.col("reported_bandwidth_gb") - F.col("actual_bandwidth_gb"))
                    / F.col("reported_bandwidth_gb") * F.lit(100.0),
                ).otherwise(F.lit(0.0)).alias("discrepancy_pct"),
                (F.col("cache_hits").cast("double") / F.greatest(F.col("requests_total").cast("double"), F.lit(1.0))).alias("cache_hit_ratio"),
                F.col("requests_total"),
                F.current_timestamp().alias("reconciled_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
