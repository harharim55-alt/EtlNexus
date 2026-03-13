"""Resource configuration for Packet Inspection Enrichment."""

resources = {
    "default": {
        "spark_driver_memory": "4g",
        "spark_executor_memory": "8g",
        "spark_executor_cores": 4,
        "spark_num_executors": 3,
    },
}
