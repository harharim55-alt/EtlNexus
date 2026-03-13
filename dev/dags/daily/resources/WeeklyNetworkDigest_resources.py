"""Resource configuration for Weekly Network Digest."""

resources = {
    "default": {
        "spark_driver_memory": "2g",
        "spark_executor_memory": "4g",
        "spark_executor_cores": 2,
        "spark_num_executors": 1,
    },
}
