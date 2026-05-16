"""Resource configuration for Network Threat Assessment."""

resources = {
    "default": {
        "spark_driver_memory": "8g",
        "spark_executor_memory": "16g",
        "spark_executor_cores": 8,
        "spark_num_executors": 6,
    },
}
