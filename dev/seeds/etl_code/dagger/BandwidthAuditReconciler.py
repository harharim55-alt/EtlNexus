"""Bandwidth Audit Reconciler - Cross-references billing invoices with metered bandwidth usage."""

from etls import bandwidth_invoices, fact_netflow_records
from base_etl import BaseETL



class BandwidthAuditReconciler(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "BandwidthAuditReconciler"

    def extract(self):
        self.invoices = bandwidth_invoices(self.start_date, self.end_date).consume()
        self.flows = fact_netflow_records(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Aggregate actual metered bytes from netflow by session, then reconcile with billing
        metered = (
            self.flows
            .groupBy("session_id")
            .agg(
                F.sum("bytes_transferred").cast("double").alias("metered_bytes"),
            )
        )

        self.result = (
            self.invoices
            .join(metered, F.col("subscription_id") == F.col("session_id"), "left")
            .select(
                F.concat_ws("-", F.lit("REC"), F.col("invoice_id")).alias("reconciliation_id"),
                F.col("circuit_id"),
                F.col("invoice_id"),
                F.coalesce(F.col("metered_bytes"), F.lit(0.0)).alias("metered_bytes"),
                F.col("bandwidth_used_mbps").alias("billed_bytes"),
                F.when(
                    F.col("bandwidth_used_mbps") > 0,
                    F.abs(F.coalesce(F.col("metered_bytes"), F.lit(0.0)) - F.col("bandwidth_used_mbps"))
                    / F.col("bandwidth_used_mbps") * F.lit(100.0),
                ).otherwise(F.lit(0.0)).alias("variance_pct"),
                F.when(
                    F.abs(F.coalesce(F.col("metered_bytes"), F.lit(0.0)) - F.col("bandwidth_used_mbps"))
                    / F.greatest(F.col("bandwidth_used_mbps"), F.lit(1.0)) > F.lit(0.1),
                    F.lit("variance_detected"),
                ).otherwise(F.lit("reconciled")).alias("status"),
                F.current_timestamp().alias("reconciled_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
