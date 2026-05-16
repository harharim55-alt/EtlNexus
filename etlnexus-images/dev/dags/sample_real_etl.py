"""Sample real PySpark ETL — demonstrates sparkMeasure metric extraction.

This module provides a spark_callable that performs actual PySpark work
(generate data, transform, aggregate, write) to validate end-to-end
metric collection through the sparkMeasure pipeline.

Usage in a DAG:
    from sample_real_etl import spark_etl_demo

    PythonOperator(
        task_id="spark_metrics_demo",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "spark_metrics_demo",
            "spark_callable": spark_etl_demo,
            "resources": {"default": {"spark_driver_memory": "1g", ...}},
            ...
        },
    )
"""


def spark_etl_demo(spark, **kwargs):
    """Perform a small but real PySpark workload for metric extraction demo.

    Creates synthetic network traffic data, performs groupBy aggregations,
    joins, and writes results to a temporary parquet file. This exercises
    enough Spark stages to produce meaningful sparkMeasure metrics including
    shuffle, I/O, and memory usage.
    """
    from pyspark.sql import functions as F

    # Generate synthetic network traffic records
    traffic_df = spark.range(0, 100_000).select(
        (F.col("id") % 50).alias("device_id"),
        (F.col("id") % 10).alias("port"),
        (F.rand() * 1_000_000).cast("long").alias("bytes_in"),
        (F.rand() * 500_000).cast("long").alias("bytes_out"),
        F.current_timestamp().alias("timestamp"),
    )

    # Generate device metadata
    devices_df = spark.range(0, 50).select(
        F.col("id").alias("device_id"),
        F.concat(F.lit("switch-"), F.col("id")).alias("hostname"),
        F.when(F.col("id") % 3 == 0, "core")
        .when(F.col("id") % 3 == 1, "distribution")
        .otherwise("access")
        .alias("tier"),
    )

    # Aggregate traffic by device (triggers shuffle)
    agg_df = traffic_df.groupBy("device_id").agg(
        F.count("*").alias("record_count"),
        F.sum("bytes_in").alias("total_bytes_in"),
        F.sum("bytes_out").alias("total_bytes_out"),
        F.avg("bytes_in").alias("avg_bytes_in"),
        F.max("bytes_in").alias("peak_bytes_in"),
    )

    # Join with device metadata (triggers another shuffle)
    enriched_df = agg_df.join(devices_df, on="device_id", how="inner")

    # Further aggregate by tier (third shuffle stage)
    tier_summary = enriched_df.groupBy("tier").agg(
        F.count("*").alias("device_count"),
        F.sum("total_bytes_in").alias("tier_bytes_in"),
        F.sum("total_bytes_out").alias("tier_bytes_out"),
    )

    # Write results to temporary parquet (triggers I/O output)
    output_path = "/tmp/spark_metrics_demo_output"
    tier_summary.write.mode("overwrite").parquet(output_path)

    row_count = tier_summary.count()
    print(f"ETL_DEMO: Wrote {row_count} tier summary records to {output_path}")
