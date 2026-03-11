"""Switch Port Collector - Periodic snapshot of network switch interface states."""

from base_etl import BaseETL

SUFFIXES = ["interfaces", "vlans", "uplinks", "configs"]


class SwitchPortCollector(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "SwitchPortCollector"

    def extract(self):
        self.ports = self.spark.table("iceberg.dagger.SwitchPortCollector")

    def transform(self):
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window

        # Deduplicate by switch_id + port_number, keeping latest collected_at
        w = Window.partitionBy("switch_id", "port_number").orderBy(F.col("collected_at").desc())
        self.result = (
            self.ports
            .withColumn("_rank", F.row_number().over(w))
            .filter(F.col("_rank") == 1)
            .drop("_rank")
            .select(
                F.col("switch_id"),
                F.col("port_number"),
                F.col("mac_address"),
                F.col("collected_at"),
                F.col("last_state_change"),
                F.col("is_active"),
                F.col("port_speed"),
                F.col("vlan_id"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
