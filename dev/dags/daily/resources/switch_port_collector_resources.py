"""Resource configuration for Switch Port Collector."""

resources = {
    "default": {
        "spark_driver_memory": "2g",
        "spark_executor_memory": "4g",
        "spark_executor_cores": 2,
        "spark_num_executors": 1,
    },
    "backbone_core": {
        "spark_executor_memory": "8g",
        "spark_num_executors": 2,
    },
}
