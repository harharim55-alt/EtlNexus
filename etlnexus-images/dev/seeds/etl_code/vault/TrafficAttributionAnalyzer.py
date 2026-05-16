"""Traffic Attribution Analyzer - Multi-hop traffic attribution across network interfaces."""

from etls import stg_http_access_logs, stg_dhcp_leases
from base_etl import BaseETL



class TrafficAttributionAnalyzer(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "TrafficAttributionAnalyzer"

    def extract(self):
        self.logs = stg_http_access_logs(self.start_date, self.end_date).consume()
        self.leases = stg_dhcp_leases(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Join HTTP access logs with DHCP leases on client_ip to attribute traffic to interfaces
        self.result = (
            self.logs
            .join(
                self.leases.select(
                    F.col("ip_address").alias("lease_ip"),
                    F.col("mac_address").alias("lease_mac"),
                    F.col("pool_name"),
                ),
                F.col("client_ip") == F.col("lease_ip"),
                "left",
            )
            .select(
                F.concat_ws("-", F.lit("ATTR"), F.col("request_id")).alias("attribution_id"),
                F.col("request_id").alias("flow_id"),
                F.coalesce(F.col("pool_name"), F.lit("unknown")).alias("interface"),
                F.when(F.col("lease_mac").isNotNull(), F.lit("internal"))
                 .otherwise(F.lit("external")).alias("hop_position"),
                F.when(F.col("status_code") < 400, F.lit(1.0))
                 .otherwise(F.lit(0.5)).alias("attribution_weight"),
                (F.col("response_time_ms").cast("double") / F.lit(10.0)).alias("bandwidth_attributed_mbps"),
                F.lit("last-touch").alias("model_type"),
                F.current_timestamp().alias("computed_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.vault.{self.etl_name}").overwritePartitions()
