"""Shared ETL runner — simulates realistic ETL execution with duration and resource usage."""

import ast
import json
import random
import time
from pathlib import Path


def run_etl(etl_name, **kwargs):
    """Execute a simulated ETL task with realistic duration and resource metrics."""
    print(f"ETL_START: {etl_name}")

    # Parse ETL code file for metadata
    etl_path = Path(f"/data/etl-code/dagger/{etl_name}.py")
    suffixes = []
    if etl_path.exists():
        tree = ast.parse(etl_path.read_text())
        docstring = ast.get_docstring(tree)
        if docstring:
            print(f"ETL_DESCRIPTION: {docstring}")
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "SUFFIXES":
                        suffixes = ast.literal_eval(node.value)

    # Check for simulated failure (raises before logging writes)
    simulate_failure = kwargs.get("simulate_failure")
    if simulate_failure:
        raise RuntimeError(simulate_failure)

    # Check for flaky failure (~40% chance of failing each run)
    simulate_flaky = kwargs.get("simulate_flaky")
    if simulate_flaky and random.random() < 0.4:
        raise RuntimeError(simulate_flaky)

    # Log write targets
    print(f"ETL_WRITES_TO: {etl_name}")
    for suffix in suffixes:
        print(f"ETL_WRITES_TO: {etl_name}_{suffix}")

    # Resolve effective resource config (default + DAG override)
    resources = kwargs.get("resources")
    dag_id = ""
    run_id = ""
    ti = kwargs.get("ti")
    if ti:
        dag_id = getattr(ti, "dag_id", "")
        run_id = getattr(ti, "run_id", "")

    effective_cfg = {}
    if resources:
        default_cfg = resources.get("default", {})
        dag_override = resources.get(dag_id, {}) if dag_id else {}
        effective_cfg = {**default_cfg, **dag_override}

    # Simulate realistic execution duration
    sleep_range = _compute_sleep_range(resources or {})
    sleep_secs = random.uniform(sleep_range[0], sleep_range[1])
    print(f"ETL_SIMULATING: sleeping {sleep_secs:.1f}s (range {sleep_range[0]}-{sleep_range[1]}s)")
    time.sleep(sleep_secs)

    # Log actual resource usage (unique per run/ETL/DAG)
    if effective_cfg:
        actual = _simulate_resource_usage(effective_cfg, etl_name, dag_id, run_id)
        print(f"ETL_RESOURCE_ACTUAL: {json.dumps(actual)}")


def _compute_sleep_range(resources: dict) -> tuple[int, int]:
    """Derive sleep duration range from resource allocation weight.

    Heavier ETLs (more memory × executors) sleep longer, simulating
    real-world processing time. Max 120 seconds.
    """
    default = resources.get("default", {})
    if not default:
        return (3, 10)  # API / no-resource tier

    mem_str = default.get("spark_executor_memory", "0g")
    mem_gb = _parse_mem_gb(mem_str)
    executors = default.get("spark_num_executors", 1)
    weight = mem_gb * executors

    if weight <= 10:
        return (3, 10)
    if weight <= 30:
        return (15, 45)
    if weight <= 60:
        return (40, 90)
    return (60, 120)


def _parse_mem_gb(mem_str: str) -> float:
    """Parse memory string like '8g' or '512m' to GB."""
    if not mem_str:
        return 0.0
    val = float(mem_str.rstrip("gGmM"))
    if mem_str[-1].lower() == "m":
        val /= 1024
    return val


def _simulate_resource_usage(
    config: dict, etl_name: str, dag_id: str, run_id: str
) -> dict:
    """Simulate actual resource usage — unique per run, ETL, and DAG.

    Uses a seeded RNG so the same (etl, dag, run) triple always produces
    the same metrics, but different triples produce different values.
    """
    seed = hash(f"{etl_name}:{dag_id}:{run_id}") & 0xFFFFFFFF
    rng = random.Random(seed)

    # Executor count varies per run (within ±2 of allocation)
    alloc_executors = config.get("spark_num_executors", 1)
    min_exec = max(1, alloc_executors - 2)
    active_executors = rng.randint(min_exec, alloc_executors)

    # Memory utilization — heavier configs tend to use more of their allocation
    mem_weight = _parse_mem_gb(config.get("spark_executor_memory", "0g"))
    if mem_weight >= 16:
        util_range = (0.65, 0.95)
    elif mem_weight >= 8:
        util_range = (0.55, 0.88)
    else:
        util_range = (0.40, 0.80)

    driver_util = rng.uniform(*util_range)
    executor_util = rng.uniform(*util_range)

    # CPU utilization correlates with resource weight
    cores = config.get("spark_executor_cores", 4)
    cpu_base = min(40 + cores * 5, 70)
    cpu_pct = round(rng.uniform(cpu_base, min(cpu_base + 25, 98)), 1)

    return {
        "driver_memory_used_mb": _mem_used_mb(
            config.get("spark_driver_memory"), driver_util
        ),
        "executor_memory_peak_mb": _mem_used_mb(
            config.get("spark_executor_memory"), executor_util
        ),
        "cpu_utilization_pct": cpu_pct,
        "executors_active": active_executors,
    }


def _mem_used_mb(alloc_str: str | None, utilization: float) -> int | None:
    """Convert allocated memory string to actual used MB given utilization ratio."""
    if not alloc_str:
        return None
    gb = _parse_mem_gb(alloc_str)
    return round(gb * utilization * 1024)
