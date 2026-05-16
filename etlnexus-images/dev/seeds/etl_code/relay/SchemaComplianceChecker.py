"""Schema Compliance Checker — Cross-reference expected vs actual schemas.

Demonstrates: Except (set difference), Intersect (set overlap), Union,
Range (spark.range for generating expected IDs), LocalTableScan
(createDataFrame for reference data), cache/persist.
"""

from base_etl import BaseETL



class SchemaComplianceChecker(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "SchemaComplianceChecker"

    def extract(self):
        self.actual_schema = self.spark.table("iceberg.relay.SchemaComplianceChecker")

    def transform(self):
        from pyspark.sql import functions as F

        # LocalTableScan: reference schema defined in-memory
        expected_fields = self.spark.createDataFrame(
            [
                ("device_id", "string", True),
                ("mac_address", "string", True),
                ("ip_address", "string", True),
                ("hostname", "string", False),
                ("subnet_id", "integer", True),
                ("vlan_id", "integer", True),
                ("device_class", "string", True),
                ("os_fingerprint", "string", False),
                ("last_seen", "timestamp", True),
                ("compliance_status", "string", True),
            ],
            ["field_name", "field_type", "is_required"],
        )

        # Range: generate expected record IDs for completeness check
        expected_ids = self.spark.range(1, 100001).withColumnRenamed("id", "expected_id")

        # Cache the actual schema columns for reuse
        actual_fields = (
            self.actual_schema
            .select("field_name", "field_type", "is_required")
            .distinct()
            .cache()
        )

        # Intersect: fields present in both expected and actual
        matched = actual_fields.intersect(expected_fields)

        # Except (subtract): fields expected but missing from actual
        missing = expected_fields.subtract(actual_fields)

        # ExceptAll: fields in actual but not expected (extra/undocumented)
        extra = actual_fields.exceptAll(expected_fields)

        # Union: combine all findings into a single report
        report = (
            matched.withColumn("status", F.lit("matched"))
            .unionByName(
                missing.withColumn("status", F.lit("missing")),
            )
            .unionByName(
                extra.withColumn("status", F.lit("extra")),
            )
        )

        self.result = report.select(
            "field_name",
            "field_type",
            "is_required",
            "status",
            F.current_timestamp().alias("checked_at"),
            F.lit(self.start_date).cast("date").alias("date"),
        )

    def load(self):
        self.result.writeTo(f"iceberg.relay.{self.etl_name}").overwritePartitions()
