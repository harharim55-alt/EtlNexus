"""Anomaly Pattern Miner — Pandas UDF-based anomaly detection on device metrics.

Demonstrates: ArrowEvalPython (pandas_udf for vectorized scoring),
FlatMapGroupsInPandas (applyInPandas for grouped anomaly detection),
MapPartitions-style operations, Python UDF execution boundaries.
"""

from etls import asset_inventory_records, field_frequency_profiles
from base_etl import BaseETL



class AnomalyPatternMiner(BaseETL):
    def __init__(self, start_date, end_date=None):
        super().__init__(start_date, end_date, schedule="daily")
        self.etl_name = "AnomalyPatternMiner"

    def extract(self):
        self.assets = asset_inventory_records(self.start_date, self.end_date).consume()
        self.profiles = field_frequency_profiles(self.start_date, self.end_date).consume()

    def transform(self):
        from pyspark.sql import functions as F
        from pyspark.sql.types import DoubleType, StructType, StructField, StringType, IntegerType

        # Pandas UDF: vectorized z-score computation
        @F.pandas_udf(DoubleType())
        def zscore(series):
            mean = series.mean()
            std = series.std()
            if std == 0 or std is None:
                return series * 0.0
            return (series - mean) / std

        # Apply pandas_udf on occurrence counts
        scored = (
            self.profiles
            .withColumn("z_score", zscore(F.col("occurrence_count").cast("double")))
            .withColumn("is_anomaly", F.abs(F.col("z_score")) > 2.0)
        )

        # applyInPandas: grouped anomaly detection per subnet
        result_schema = StructType([
            StructField("subnet_id", IntegerType()),
            StructField("anomaly_count", IntegerType()),
            StructField("mean_occurrences", DoubleType()),
            StructField("std_occurrences", DoubleType()),
            StructField("max_zscore", DoubleType()),
            StructField("pattern_label", StringType()),
        ])

        def detect_anomalies(pdf):
            import pandas as pd
            z = pdf["z_score"]
            anom_count = int((z.abs() > 2.0).sum())
            label = "normal"
            if anom_count > 5:
                label = "high_anomaly"
            elif anom_count > 0:
                label = "low_anomaly"
            return pd.DataFrame([{
                "subnet_id": pdf["subnet_id"].iloc[0],
                "anomaly_count": anom_count,
                "mean_occurrences": float(pdf["occurrence_count"].mean()),
                "std_occurrences": float(pdf["occurrence_count"].std() or 0),
                "max_zscore": float(z.abs().max() or 0),
                "pattern_label": label,
            }])

        subnet_anomalies = scored.groupby("subnet_id").applyInPandas(
            detect_anomalies, schema=result_schema
        )

        self.result = (
            subnet_anomalies
            .withColumn("mined_at", F.current_timestamp())
            .withColumn("date", F.lit(self.start_date).cast("date"))
        )

    def load(self):
        self.result.writeTo(f"iceberg.relay.{self.etl_name}").overwritePartitions()
