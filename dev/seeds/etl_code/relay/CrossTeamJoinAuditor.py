"""Cross-Team Join Auditor — Validates join key integrity across team boundaries.

Demonstrates: BroadcastHashJoin (broadcast hint), SortMergeJoin (large tables),
CartesianProduct (crossJoin for small reference), LeftSemi join, LeftAnti join,
LocalTableScan (createDataFrame), Union.
"""

from etls import asset_inventory_records
from base_etl import BaseETL



class CrossTeamJoinAuditor(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "CrossTeamJoinAuditor"

    def extract(self):
        self.assets = asset_inventory_records(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # LocalTableScan: known device fingerprints as reference
        known_macs = self.spark.createDataFrame(
            [(m,) for m in [
                "00:1A:2B:3C:4D:5E", "AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66",
                "DE:AD:BE:EF:00:01", "CA:FE:BA:BE:00:02", "F0:F0:F0:F0:F0:F0",
            ]],
            ["known_mac"],
        )

        # BroadcastHashJoin: small reference broadcast to all executors
        severity_labels = self.spark.createDataFrame(
            [("critical", 4), ("high", 3), ("medium", 2), ("low", 1)],
            ["risk_bucket", "severity_rank"],
        )
        asset_types = (
            self.assets
            .select(
                "mac_address",
                F.when(F.col("days_since_seen") > 60, F.lit("critical"))
                .when(F.col("days_since_seen") > 30, F.lit("high"))
                .when(F.col("days_since_seen") > 7, F.lit("medium"))
                .otherwise(F.lit("low")).alias("risk_bucket"),
            )
        )
        assets_ranked = asset_types.join(
            F.broadcast(severity_labels),
            on="risk_bucket",
            how="inner",
        )

        # LeftSemi join: assets that match known fingerprints
        assets_with_fingerprints = self.assets.join(
            known_macs,
            self.assets["mac_address"] == known_macs["known_mac"],
            "left_semi",
        )

        # LeftAnti join: orphan assets missing from known fingerprints
        orphan_assets = self.assets.join(
            known_macs,
            self.assets["mac_address"] == known_macs["known_mac"],
            "left_anti",
        )

        # CrossJoin: small reference — all team-subnet combinations
        teams = self.spark.createDataFrame(
            [("dagger",), ("vault",), ("prism",), ("relay",), ("oasis",)],
            ["team_name"],
        )
        subnets = self.spark.createDataFrame(
            [(10,), (20,), (30,), (50,), (100,)],
            ["subnet_ref"],
        )
        coverage_matrix = teams.crossJoin(subnets)

        # Union: combine orphan + matched reports
        self.result = (
            orphan_assets
            .select(
                "mac_address",
                "ip_address",
                "subnet_id",
                F.lit("orphan").alias("audit_status"),
                F.lit("missing_fingerprint").alias("issue_type"),
            )
            .unionByName(
                assets_with_fingerprints
                .select(
                    "mac_address",
                    "ip_address",
                    "subnet_id",
                    F.lit("matched").alias("audit_status"),
                    F.lit("none").alias("issue_type"),
                )
            )
            .withColumn("audited_at", F.current_timestamp())
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.relay.{self.etl_name}").overwritePartitions()
