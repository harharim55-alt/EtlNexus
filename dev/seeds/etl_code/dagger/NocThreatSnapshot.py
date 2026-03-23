"""NOC Threat Snapshot - Top-level KPI rollup for network operations center."""

from etls import fact_bandwidth_reconciled, ml_link_failure_features
from base_etl import BaseETL

SUFFIXES = ["bandwidth_daily", "bandwidth_weekly", "bandwidth_monthly", "throughput", "capacity_total", "outage_daily", "outage_weekly", "latency", "jitter", "uptime", "mttr", "packets_per_second", "endpoints_active", "endpoints_total", "failover_7d", "failover_30d", "handshake_funnel", "traffic_cohort_analysis", "noc_board_summary"]


class NocThreatSnapshot(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "NocThreatSnapshot"

    def extract(self):
        self.bandwidth = fact_bandwidth_reconciled(self.start_date, self.end_date).consume()
        self.failures = ml_link_failure_features(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Aggregate bandwidth reconciliation data for KPIs
        bw_agg = (
            self.bandwidth
            .agg(
                F.sum("metered_bytes").alias("total_metered"),
                F.max("metered_bytes").alias("peak_metered"),
                F.countDistinct("circuit_id").alias("active_circuits"),
            )
        )

        # Aggregate link failure features for health KPIs
        fail_agg = (
            self.failures
            .agg(
                F.avg("failure_probability").alias("avg_failure_rate"),
                F.avg("health_score").alias("avg_health"),
                F.countDistinct("link_id").alias("total_links"),
            )
        )

        self.result = (
            bw_agg.crossJoin(fail_agg)
            .select(
                F.lit(self.start_date).cast("date").alias("snapshot_date"),
                (F.coalesce(F.col("total_metered"), F.lit(0.0)) / F.lit(1e9)).alias("total_bandwidth_gbps"),
                (F.coalesce(F.col("peak_metered"), F.lit(0.0)) / F.lit(1e9)).alias("peak_throughput_gbps"),
                F.coalesce(F.col("active_circuits"), F.lit(0)).cast("long").alias("active_endpoints"),
                F.coalesce(F.col("avg_failure_rate"), F.lit(0.0)).alias("link_failure_rate"),
                F.coalesce(F.col("avg_health"), F.lit(1.0)).alias("avg_health_score"),
                # avg_latency_ms: derived from total bandwidth as proxy
                (F.coalesce(F.col("total_metered"), F.lit(0.0)) / F.greatest(F.coalesce(F.col("total_links").cast("double"), F.lit(1.0)), F.lit(1.0)) / F.lit(1e6)).alias("avg_latency_ms"),
                F.current_timestamp().alias("generated_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
