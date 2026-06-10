"""Resource configuration for Asset Inventory Snapshot."""

resources = {
    "default": {
        "spark_driver_memory": "1g",
        "spark_executor_memory": "1g",
        "spark_executor_cores": 1,
        "spark_num_executors": 1,
    },
    "data_quality_audit": {
        "spark_executor_memory": "2g",
        "spark_num_executors": 1,
    },
}
