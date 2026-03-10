"""Resource configuration for Link Failure Prediction."""

resources = {
    "default": {
        "spark_driver_memory": "8g",
        "spark_executor_memory": "16g",
        "spark_executor_cores": 8,
        "spark_num_executors": 5,
    },
}
