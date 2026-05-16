"""Asset Inventory Snapshot — Deduplicated device inventory with sampled validation.

Demonstrates: Scan (Iceberg), Window, Deduplicate (dropDuplicates), Sample,
withColumn, withColumnRenamed, Filter, Project, Sort, Limit.
"""

from base_etl import BaseETL



class AssetInventorySnapshot(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "AssetInventorySnapshot"

    def extract(self):
        self.assets = self.spark.table("iceberg.relay.AssetInventorySnapshot")

    def transform(self):
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window

        # Window: rank assets by last_seen within each subnet
        w = Window.partitionBy("subnet_id").orderBy(F.col("last_seen").desc())
        ranked = (
            self.assets
            .withColumn("freshness_rank", F.row_number().over(w))
            .withColumn("days_since_seen",
                        F.datediff(F.current_date(), F.col("last_seen")))
            .withColumnRenamed("asset_type", "device_category")
            .withColumn("is_stale", F.col("days_since_seen") > 30)
        )

        # Deduplicate: keep one record per mac_address
        deduped = ranked.dropDuplicates(["mac_address"])

        # Filter: active devices only
        active = deduped.filter(
            (F.col("is_stale") == False) & F.col("mac_address").isNotNull()
        )

        # Sort + Limit: top 10000 most recently seen
        top_assets = (
            active
            .orderBy(F.col("last_seen").desc())
            .limit(10000)
        )

        # Sample: 5% random sample for audit validation
        self.audit_sample = top_assets.sample(0.05, seed=42)

        # Project: final output columns (rename back to match table schema)
        self.result = top_assets.select(
            "mac_address",
            "subnet_id",
            F.col("device_category").alias("asset_type"),
            "hostname",
            "ip_address",
            "last_seen",
            "os_fingerprint",
            "tags_csv",
            "days_since_seen",
            F.lit(self.start_date).cast("date").alias("date"),
        )

    def load(self):
        self.result.writeTo(f"iceberg.relay.{self.etl_name}").overwritePartitions()
