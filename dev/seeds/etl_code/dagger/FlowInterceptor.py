"""Flow Interceptor - Raw network flow records from switches and routers."""

from etls import switch_interface_snapshot
from base_etl import BaseETL

SUFFIXES = []


class FlowInterceptor(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="hourly")
        self.etl_name = "FlowInterceptor"

    def extract(self):
        self.ports = switch_interface_snapshot(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Enrich flow records from switch interface data
        self.result = (
            self.ports
            .filter(F.col("is_active") == True)
            .select(
                F.concat_ws("-", F.lit("flow"), F.col("switch_id").cast("string"), F.col("port_number")).alias("flow_id"),
                F.col("mac_address").alias("src_ip"),
                F.concat_ws(".", F.lit("10"), F.col("vlan_id").cast("string"), F.lit("0"), F.lit("1")).alias("dst_ip"),
                F.col("collected_at").alias("capture_time"),
                F.concat_ws("-", F.lit("sess"), F.col("switch_id").cast("string")).alias("session_id"),
                F.when(F.col("port_speed") == "1Gbps", F.lit("TCP"))
                 .when(F.col("port_speed") == "10Gbps", F.lit("UDP"))
                 .otherwise(F.lit("ICMP")).alias("protocol"),
                (F.col("vlan_id") * F.lit(1024)).alias("bytes_transferred"),
                F.current_timestamp().alias("collected_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
            .withColumn("hourkey", F.lit(self.hourkey))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
