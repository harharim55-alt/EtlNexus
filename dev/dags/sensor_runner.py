"""Shared bouncer runner — simulates data-ingestion bouncer execution.

Unlike etl_runner.py, bouncers get ALL metadata from op_kwargs.
No code-file reading, no ETL_WRITES_TO output.
"""

import random
import time


def run_bouncer(sensor_name: str, **kwargs):
    """Execute a simulated bouncer task with description logging."""
    print(f"BOUNCER_START: {sensor_name}")

    description = kwargs.get("description", "")
    if description:
        print(f"BOUNCER_DESCRIPTION: {description}")

    # Bouncers are fast ingestion tasks — 2-6 seconds
    sleep_secs = random.uniform(2, 6)
    print(f"BOUNCER_SIMULATING: sleeping {sleep_secs:.1f}s")
    time.sleep(sleep_secs)

    print(f"BOUNCER_COMPLETE: {sensor_name}")
