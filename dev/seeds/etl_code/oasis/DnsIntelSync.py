"""DNS Intel Sync - Hourly sync of DNS zone records and resolution cache."""

from base_etl import BaseETL

SUFFIXES = ["a_records", "cname_records", "mx_records", "txt_records", "ptr_records"]


class DnsIntelSync(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "DnsIntelSync"

    def extract(self):
        self.records = self.spark.table("iceberg.oasis.DnsIntelSync")

    def transform(self):
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window

        # Deduplicate by record_id, keeping latest last_modified_date
        w = Window.partitionBy("record_id").orderBy(F.col("last_modified_date").desc())
        self.result = (
            self.records
            .withColumn("_rank", F.row_number().over(w))
            .filter(F.col("_rank") == 1)
            .drop("_rank")
            .select(
                F.col("record_id"),
                F.col("zone_name"),
                F.col("record_type"),
                F.col("ttl"),
                F.col("record_value"),
                F.col("status"),
                F.col("created_date"),
                F.col("last_modified_date"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.oasis.{self.etl_name}").overwritePartitions()
