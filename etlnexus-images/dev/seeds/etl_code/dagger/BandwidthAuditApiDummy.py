"""Bandwidth Audit API - Serves reconciled bandwidth data to billing dashboards."""

from etls import fact_bandwidth_reconciled, bandwidth_invoices
from base_etl import BaseETL



class BandwidthAuditApi(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "BandwidthAuditApiDummy"

    def extract(self):
        self.bandwidth = fact_bandwidth_reconciled(self.start_date, self.end_date).consume()
        self.invoices = bandwidth_invoices(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Join reconciled bandwidth with invoice data for API consumption
        self.result = (
            self.bandwidth
            .join(
                self.invoices.select(
                    F.col("invoice_id").alias("inv_id"),
                    F.col("bandwidth_allocated_mbps"),
                    F.col("billing_tier"),
                    F.col("status").alias("invoice_status"),
                ),
                F.col("invoice_id") == F.col("inv_id"),
                "left",
            )
            .select(
                F.col("reconciliation_id"),
                F.col("circuit_id"),
                F.col("invoice_id"),
                F.col("metered_bytes"),
                F.col("billed_bytes"),
                F.col("variance_pct"),
                F.col("status"),
                F.coalesce(F.col("bandwidth_allocated_mbps"), F.lit(0.0)).alias("bandwidth_allocated_mbps"),
                F.coalesce(F.col("billing_tier"), F.lit("unknown")).alias("billing_tier"),
                F.col("reconciled_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        # API tier: result is served directly, no Iceberg write
        pass
