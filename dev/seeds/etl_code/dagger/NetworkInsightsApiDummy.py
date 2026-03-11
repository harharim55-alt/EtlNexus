"""Network Insights API - Serves device health scores and failure prediction data."""

from etls import ml_link_failure_features
from base_etl import BaseETL

SUFFIXES = []


class NetworkInsightsApi(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "NetworkInsightsApiDummy"

    def extract(self):
        self.failures = ml_link_failure_features(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F

        # Project link failure features and NOC dashboard data for API consumption
        self.result = (
            self.failures
            .select(
                F.col("link_id"),
                F.col("hours_since_last_flap"),
                F.col("avg_error_rate"),
                F.col("crc_errors_30d"),
                F.col("packet_loss_events_90d"),
                F.col("failure_probability"),
                F.col("health_score"),
                F.col("scored_at"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        # API tier: result is served directly, no Iceberg write
        pass
