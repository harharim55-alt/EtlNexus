"""Resource configuration for Device Fingerprint Enrichment."""

resources = {
    "default": {
        "spark_driver_memory": "8g",
        "spark_executor_memory": "16g",
        "spark_executor_cores": 8,
        "spark_num_executors": 5,
    },
    "backbone_core": {
        "spark_executor_memory": "24g",
        "spark_num_executors": 8,
    },
}
