"""HTTP Access Log Ingest - Daily HTTP access log sessions and request events."""

from base_etl import BaseETL

SUFFIXES = ["sessions", "error_codes"]


class HttpAccessLogIngest(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "http_access_log_ingest"

    def extract(self):
        self.logs = self.spark.table("iceberg.dagger.http_access_log_ingest")

    def transform(self):
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window

        # Deduplicate by request_id, keeping latest request_time
        w = Window.partitionBy("request_id").orderBy(F.col("request_time").desc())
        self.result = (
            self.logs
            .withColumn("_rank", F.row_number().over(w))
            .filter(F.col("_rank") == 1)
            .drop("_rank")
            .select(
                F.col("request_id"),
                F.col("client_ip"),
                F.col("request_path"),
                F.col("method"),
                F.col("status_code"),
                F.col("user_agent"),
                F.col("response_time_ms"),
                F.col("request_time"),
            )
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.dagger.{self.etl_name}").overwritePartitions()
