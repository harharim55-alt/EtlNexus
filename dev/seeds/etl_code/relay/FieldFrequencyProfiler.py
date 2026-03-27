"""Field Frequency Profiler — Explode nested arrays and profile value distributions.

Demonstrates: Generate (explode, posexplode), Aggregate (groupBy + multiple aggs),
HashAggregate partial/final phases, Coalesce, Repartition (Exchange RangePartitioning).
"""

from etls import asset_inventory_records
from base_etl import BaseETL



class FieldFrequencyProfiler(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "FieldFrequencyProfiler"

    def extract(self):
        self.assets = asset_inventory_records(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Repartition by subnet for better parallelism
        partitioned = self.assets.repartition(50, "subnet_id")

        # Generate (explode): split CSV tags into array, then explode into rows
        with_tags_array = partitioned.withColumn(
            "tags_array", F.split(F.col("tags_csv"), ",")
        )
        exploded_tags = (
            with_tags_array
            .filter(F.col("tags_csv").isNotNull())
            .select("mac_address", "subnet_id", F.explode("tags_array").alias("tag"))
        )

        # Generate (posexplode): get tag positions for ordering analysis
        positioned_tags = (
            with_tags_array
            .filter(F.col("tags_csv").isNotNull())
            .select("mac_address", F.posexplode("tags_array").alias("tag_position", "tag_value"))
        )

        # Aggregate: profile tag frequency per subnet
        tag_frequency = (
            exploded_tags
            .groupBy("subnet_id", "tag")
            .agg(
                F.count("*").alias("occurrence_count"),
                F.countDistinct("mac_address").alias("unique_devices"),
                F.collect_set("mac_address").alias("device_sample"),
            )
        )

        # Aggregate: overall field nullability profiling
        null_profile = (
            partitioned
            .agg(
                F.count("*").alias("total_rows"),
                F.sum(F.when(F.col("hostname").isNull(), 1).otherwise(0)).alias("null_hostname"),
                F.sum(F.when(F.col("ip_address").isNull(), 1).otherwise(0)).alias("null_ip"),
                F.sum(F.when(F.col("os_fingerprint").isNull(), 1).otherwise(0)).alias("null_os"),
                F.avg(F.col("days_since_seen").cast("double")).alias("avg_days_since_seen"),
                F.percentile_approx(F.col("days_since_seen").cast("double"), 0.95).alias("p95_days_since_seen"),
            )
        )

        # Coalesce: reduce partitions for output
        self.result = (
            tag_frequency
            .drop("device_sample")
            .withColumn("profiled_at", F.current_timestamp())
            .withColumn("date", F.lit(self.start_date).cast("date"))
            .coalesce(10)
        )

    def load(self):
        self.result.writeTo(f"iceberg.relay.{self.etl_name}").overwritePartitions()
