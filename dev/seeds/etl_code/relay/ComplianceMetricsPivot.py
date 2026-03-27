"""Compliance Metrics Pivot — Pivot and unpivot compliance scores for dashboards.

Demonstrates: Unpivot/melt (converting wide to long format), Pivot (long to wide),
Expand (rollup/cube aggregations), complex aggregate expressions.
"""

from etls import cross_team_audit_results
from base_etl import BaseETL



class ComplianceMetricsPivot(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "ComplianceMetricsPivot"

    def extract(self):
        self.audit_results = cross_team_audit_results(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Aggregate: count by subnet and status (pivot source)
        status_counts = (
            self.audit_results
            .groupBy("subnet_id")
            .pivot("audit_status", ["matched", "orphan"])
            .agg(F.count("mac_address"))
            .na.fill(0)
        )

        # Unpivot/melt: convert wide status counts back to long format
        long_format = status_counts.unpivot(
            ["subnet_id"],
            ["matched", "orphan"],
            "status_type",
            "device_count",
        )

        # Rollup: hierarchical aggregation with subtotals
        rollup_summary = (
            self.audit_results
            .groupBy("subnet_id", "audit_status")
            .agg(
                F.count("*").alias("total_records"),
                F.countDistinct("mac_address").alias("unique_devices"),
            )
            .rollup("subnet_id", "audit_status")
            .agg(
                F.sum("total_records").alias("total_records"),
                F.sum("unique_devices").alias("unique_devices"),
            )
        )

        # Cube: cross-dimensional summary
        cube_summary = (
            self.audit_results
            .cube("subnet_id", "issue_type")
            .agg(
                F.count("*").alias("record_count"),
                F.countDistinct("mac_address").alias("device_count"),
            )
        )

        self.result = (
            long_format
            .withColumn("computed_at", F.current_timestamp())
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.relay.{self.etl_name}").overwritePartitions()
