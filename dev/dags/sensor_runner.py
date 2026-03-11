"""Shared sensor runner — simulates data-ingestion sensor execution.

Unlike etl_runner.py, sensors get ALL metadata from op_kwargs.
No code-file reading, no ETL_WRITES_TO output.
"""

import random
import time


def run_sensor(sensor_name: str, **kwargs):
    """Execute a simulated sensor task with volume logging."""
    print(f"SENSOR_START: {sensor_name}")

    description = kwargs.get("description", "")
    if description:
        print(f"SENSOR_DESCRIPTION: {description}")

    volume_per_day = kwargs.get("volume_per_day")

    # Sensors are fast ingestion tasks — 2-6 seconds
    sleep_secs = random.uniform(2, 6)
    print(f"SENSOR_SIMULATING: sleeping {sleep_secs:.1f}s")
    time.sleep(sleep_secs)

    if volume_per_day:
        print(f"SENSOR_VOLUME: {volume_per_day}")

    print(f"SENSOR_COMPLETE: {sensor_name}")
