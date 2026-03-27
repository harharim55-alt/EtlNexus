"""Quality Alert API Dummy — Publishes quality alerts via REST API.

Demonstrates: API task pattern (non-ETL task that publishes data externally).
"""

from etls import quality_scorecard_results
from base_etl import BaseETL



class QualityAlertApiDummy(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "QualityAlertApiDummy"

    def extract(self):
        self.scores = quality_scorecard_results(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Filter critical alerts only for API push
        self.result = (
            self.scores
            .filter(F.col("alert_level") == "critical")
            .select(
                "subnet_id",
                "composite_score",
                "anomaly_count",
                "quality_tier",
                "alert_level",
                F.current_timestamp().alias("published_at"),
                F.lit(self.start_date).cast("date").alias("date"),
            )
        )

    def load(self):
        self.result.writeTo(f"iceberg.relay.{self.etl_name}").overwritePartitions()
