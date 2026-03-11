"""DHCP Lease Sync - Ingests leases, pools, and reservations from DHCP server API."""

from base_etl import BaseETL

SUFFIXES = ["pools", "reservations"]


class DhcpLeaseSync(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "DhcpLeaseSync"

    def extract(self):
        self.leases = self.spark.table("iceberg.dagger.DhcpLeaseSync")

    def transform(self):
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window

        # Deduplicate by lease_id, keeping latest lease_start
        w = Window.partitionBy("lease_id").orderBy(F.col("lease_start").desc())
        self.result = (
            self.leases
            .withColumn("_rank", F.row_number().over(w))
            .filter(F.col("_rank") == 1)
            .drop("_rank")
            .select(
                F.col("lease_id"),
                F.col("ip_address"),
                F.col("mac_address"),
                F.col("hostname"),
                F.col("pool_name"),
                F.col("lease_state"),
                F.col("lease_start"),
                F.col("lease_expiry"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
