"""Shared ETL runner — executes ETL tasks with real or simulated resource metrics.

Dual-mode operation:
- Real mode (spark_callable provided): Creates SparkSession, collects metrics via
  sparkMeasure, and logs actual resource usage.
- Simulation mode (no spark_callable): Sleeps and generates deterministic fake
  metrics for development/demo purposes.
"""

import ast
import importlib
import json
import logging
import random
import re
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def run_etl(etl_name, spark_callable=None, **kwargs):
    """Execute an ETL task with real Spark metrics or simulated metrics.

    Args:
        etl_name: Name of the ETL task.
        spark_callable: Optional function(spark, **kwargs) that performs real
            PySpark work. If provided, a SparkSession is created and metrics
            are collected via sparkMeasure. If None, simulation mode is used.
        **kwargs: Airflow op_kwargs (resources, ti, needs, etc.)
    """
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

    # Auto-create spark_callable from ETL class if not explicitly provided
    if spark_callable is None and etl_path.exists():
        spark_callable = _make_etl_callable(etl_name, ti)

    if spark_callable is not None:
        # --- REAL MODE: run actual PySpark with metrics collection ---
        actual = _run_real_spark(etl_name, spark_callable, effective_cfg, kwargs)
    else:
        # --- SIMULATION MODE: sleep + deterministic fake metrics ---
        sleep_range = _compute_sleep_range(resources or {})
        sleep_secs = random.uniform(sleep_range[0], sleep_range[1])
        print(f"ETL_SIMULATING: sleeping {sleep_secs:.1f}s (range {sleep_range[0]}-{sleep_range[1]}s)")
        time.sleep(sleep_secs)

        actual = None
        if effective_cfg:
            actual = _simulate_resource_usage(effective_cfg, etl_name, dag_id, run_id)
            actual["metrics_source"] = "simulation"

    if actual:
        print(f"ETL_RESOURCE_ACTUAL: {json.dumps(actual)}")


def _run_real_spark(
    etl_name: str, spark_callable, config: dict, kwargs: dict
) -> dict:
    """Create a SparkSession, run the callable, and collect real metrics."""
    spark = _create_spark_session(etl_name, config)
    try:
        # Try sparkMeasure metrics collection; fall back to plain execution
        try:
            from spark_metrics_collector import collect_spark_metrics
            with collect_spark_metrics(spark) as collector:
                spark_callable(spark, **kwargs)
            return collector.get_metrics()
        except Exception as metrics_err:
            # If sparkMeasure fails, run without metrics collection
            logger.warning(
                "sparkMeasure unavailable for %s (%s), running without metrics",
                etl_name, type(metrics_err).__name__,
            )
            spark_callable(spark, **kwargs)
            return {"metrics_source": "spark_no_metrics"}
    except Exception:
        logger.exception("Spark task %s failed", etl_name)
        raise
    finally:
        spark.stop()


def _create_spark_session(etl_name: str, config: dict):
    """Create a SparkSession configured from the resource allocation dict."""
    from pyspark.sql import SparkSession

    builder = SparkSession.builder.appName(etl_name)

    # Map resource config to Spark properties
    if config.get("spark_driver_memory"):
        builder = builder.config("spark.driver.memory", config["spark_driver_memory"])
    if config.get("spark_executor_memory"):
        builder = builder.config("spark.executor.memory", config["spark_executor_memory"])
    if config.get("spark_executor_cores"):
        builder = builder.config("spark.executor.cores", str(config["spark_executor_cores"]))
    if config.get("spark_num_executors"):
        builder = builder.config("spark.executor.instances", str(config["spark_num_executors"]))

    # Iceberg catalog + sparkMeasure JARs
    builder = builder.config(
        "spark.jars.packages",
        "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.1,"
        "ch.cern.sparkmeasure:spark-measure_2.12:0.24",
    )
    builder = builder.config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
    builder = builder.config("spark.sql.catalog.iceberg.type", "rest")
    builder = builder.config("spark.sql.catalog.iceberg.uri", "http://iceberg-rest:8181")
    builder = builder.config(
        "spark.sql.extensions",
        "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    )

    # Enable event logging for future History Server compatibility
    builder = builder.config("spark.eventLog.enabled", "true")
    builder = builder.config("spark.eventLog.dir", "/tmp/spark-events")

    # Local mode for dev
    builder = builder.master("local[*]")

    return builder.getOrCreate()


def _compute_sleep_range(resources: dict) -> tuple[int, int]:
    """Derive sleep duration range from resource allocation weight.

    Heavier ETLs (more memory x executors) sleep longer, simulating
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

    # Executor count varies per run (within +/-2 of allocation)
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


def _make_etl_callable(etl_name: str, ti=None):
    """Create a spark_callable from an ETL class file.

    Dynamically imports the ETL module, finds the BaseETL subclass,
    and returns a callable that runs the ETL and extracts the Spark plan.
    """
    from datetime import datetime, timedelta

    # Resolve execution date from Airflow TaskInstance
    if ti and hasattr(ti, "execution_date") and ti.execution_date:
        start_date = ti.execution_date
    else:
        start_date = datetime(2026, 3, 10)

    etl_code_path = "/data/etl-code"
    if etl_code_path not in sys.path:
        sys.path.insert(0, etl_code_path)

    try:
        mod = importlib.import_module(f"dagger.{etl_name}")
    except ImportError:
        logger.warning("Could not import ETL module dagger.%s", etl_name)
        return None

    # Find the ETL class (has extract/transform/load methods)
    etl_class = None
    for obj in vars(mod).values():
        if (
            isinstance(obj, type)
            and hasattr(obj, "extract")
            and hasattr(obj, "transform")
            and hasattr(obj, "load")
            and obj.__name__ != "BaseETL"
        ):
            etl_class = obj
            break

    if etl_class is None:
        logger.warning("No ETL class found in dagger.%s", etl_name)
        return None

    def callable(spark, **kwargs):
        etl = etl_class(start_date)
        etl.spark = spark  # Use the SparkSession from run_etl
        etl.run()  # extract -> transform -> load

        # Extract execution plan tree with real metrics.
        # Strategy: tree structure from the result DataFrame's plan,
        # metrics from the status store's planGraph (matched by desc).
        if hasattr(etl, "result") and etl.result is not None:
            try:
                metrics_map = _get_graph_metrics(spark)
                plan = etl.result._jdf.queryExecution().executedPlan()
                plan_tree = _extract_plan_tree(plan, metrics_map)
                if plan_tree:
                    print(f"ETL_EXECUTION_PLAN: {json.dumps(plan_tree)}")
            except Exception:
                logger.warning("Could not extract execution plan for %s", etl_name, exc_info=True)

    return callable


def _get_graph_metrics(spark) -> dict:
    """Get real metric values from the SQL status store's planGraph.

    Returns dict mapping cleaned_desc (str) → {display_key: formatted_value}.
    The key is the first line of the node description with column IDs stripped,
    which allows matching against the result DataFrame's plan nodes regardless
    of different accumulator/column ID assignments.
    """
    try:
        store = spark._jsparkSession.sharedState().statusStore()
        exec_list = store.executionsList()
        if exec_list.isEmpty():
            return {}

        last_exec = exec_list.last()
        exec_id = last_exec.executionId()

        # Get all accumulator values: Scala Map[Long, String]
        metric_values = store.executionMetrics(exec_id)
        acc_map = {}
        it = metric_values.iterator()
        while it.hasNext():
            pair = it.next()
            acc_map[int(pair._1())] = str(pair._2())

        if not acc_map:
            return {}

        # Get plan graph nodes — each has a desc and metric accumulator IDs
        graph = store.planGraph(exec_id)
        nodes = graph.allNodes()
        result = {}
        for i in range(nodes.size()):
            n = nodes.apply(i)
            desc = str(n.desc())
            # Key by first line with column IDs stripped (matches plan node toString)
            key = _strip_col_ids(desc.split("\n")[0].strip())[:120]
            metrics = {}
            metric_seq = n.metrics()
            for j in range(metric_seq.size()):
                m = metric_seq.apply(j)
                name = str(m.name())
                if name in _METRIC_SKIP:
                    continue
                acc_id = int(m.accumulatorId())
                if acc_id in acc_map:
                    val = _clean_metric_value(acc_map[acc_id])
                    if not val or _is_zero_metric(val):
                        continue
                    display_key = _METRIC_DISPLAY.get(name, name)
                    metrics[display_key] = _format_metric_value(name, val)
            if metrics:
                result[key] = metrics

        return result

    except Exception:
        logger.warning("Could not get graph metrics from status store", exc_info=True)
        return {}


# Node types to skip (wrappers that add no semantic value)
_SKIP_NODES = {
    "AdaptiveSparkPlan",
    "WholeStageCodegen",
    "InputAdapter",
    "ColumnarToRow",
    "BroadcastQueryStage",
    "ShuffleQueryStage",
    "CommandResult",
    "Execute",
}

_node_counter = 0


def _extract_plan_tree(plan_node, metrics_map: dict | None = None) -> dict | None:
    """Extract a Spark physical plan tree via py4j with optional metrics."""
    global _node_counter
    _node_counter = 0
    return _traverse_plan_node(plan_node, metrics_map or {})


def _traverse_plan_node(node, metrics_map: dict) -> dict | None:
    """Traverse a plan node, matching metrics by stripped description."""
    global _node_counter

    node_name = node.nodeName()

    # AdaptiveSparkPlan wraps the final plan after AQE — use executedPlan
    if node_name == "AdaptiveSparkPlan":
        try:
            return _traverse_plan_node(node.executedPlan(), metrics_map)
        except Exception:
            pass

    # Skip wrapper nodes — recurse into their children
    if node_name in _SKIP_NODES:
        children = node.children()
        child_count = children.length()
        if child_count == 1:
            return _traverse_plan_node(children.apply(0), metrics_map)
        result_children = []
        for i in range(child_count):
            child_result = _traverse_plan_node(children.apply(i), metrics_map)
            if child_result:
                result_children.append(child_result)
        if len(result_children) == 1:
            return result_children[0]
        if result_children:
            _node_counter += 1
            return {
                "id": _node_counter,
                "name": node_name,
                "type": "transform",
                "detail": "",
                "full_detail": "",
                "metrics": {},
                "children": result_children,
            }
        return None

    node_type = _classify_node(node_name)

    # Extract detail via toString() (most reliable py4j method on SparkPlan)
    raw_detail = node_name
    try:
        raw_detail = str(node)
        first_line = raw_detail.split("\n")[0].strip()
        if first_line:
            raw_detail = first_line
    except Exception:
        pass
    detail = _extract_detail(node_name, raw_detail)
    full_detail = _extract_full_detail(node_name, raw_detail)

    # Match metrics by stripped description (column IDs removed so both
    # the result plan and the write execution's plan graph match)
    metrics = {}
    try:
        key = _strip_col_ids(raw_detail)[:120]
        metrics = metrics_map.get(key, {})
    except Exception:
        pass

    # Recurse into children
    result_children = []
    try:
        children = node.children()
        child_count = children.length()
        for i in range(child_count):
            child_result = _traverse_plan_node(children.apply(i), metrics_map)
            if child_result:
                result_children.append(child_result)
    except Exception:
        pass

    _node_counter += 1
    return {
        "id": _node_counter,
        "name": _clean_node_name(node_name),
        "type": node_type,
        "detail": detail,
        "full_detail": full_detail,
        "metrics": metrics,
        "children": result_children,
    }


def _classify_node(name: str) -> str:
    """Classify a Spark plan node into read/write/shuffle/transform."""
    lower = name.lower()
    if "scan" in lower or "datasource" in lower:
        return "read"
    if "write" in lower or "insert" in lower or "overwrite" in lower or "append" in lower:
        return "write"
    if "join" in lower or "exchange" in lower or "sort" in lower or "shuffle" in lower:
        return "shuffle"
    return "transform"


def _clean_node_name(name: str) -> str:
    """Simplify verbose Spark node names, preserving join strategy."""
    for prefix in ("Batched",):
        if name.startswith(prefix) and len(name) > len(prefix):
            name = name[len(prefix):]
    return name


# ── Detail extraction ─────────────────────────────────────────────

# Strip Spark column ID suffixes like #42, #5L
_COL_ID_RE = re.compile(r"#\d+[L]?")


def _split_top_level(s: str, sep: str = ",") -> list[str]:
    """Split string on separator only at top-level (not inside parentheses)."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth <= 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def _balance_parens(s: str) -> str:
    """Ensure parentheses are balanced by appending/prepending as needed."""
    opens = s.count("(")
    closes = s.count(")")
    if opens > closes:
        s += ")" * (opens - closes)
    elif closes > opens:
        s = "(" * (closes - opens) + s
    return s


def _strip_col_ids(s: str) -> str:
    return _COL_ID_RE.sub("", s)


def _extract_full_detail(node_name: str, simple_str: str) -> str:
    """Return full untruncated detail string for modal/expanded view."""
    clean = _strip_col_ids(simple_str)
    lower = node_name.lower()

    try:
        if "join" in lower:
            return _parse_join_full(clean)
        if "filter" in lower:
            return _parse_filter_full(clean)
        if "aggregate" in lower:
            return _parse_aggregate_full(clean)
        if "scan" in lower or "datasource" in lower:
            return _parse_scan_full(clean)
        if "sort" in lower and "merge" not in lower:
            return _parse_sort_full(clean)
        if "exchange" in lower:
            return _parse_exchange_detail(clean)
        if node_name == "Project":
            return _parse_project_full(clean)
    except Exception:
        pass

    if clean and clean != node_name and len(clean) > len(node_name) + 3:
        return _balance_parens(clean)
    return ""


def _extract_detail(node_name: str, simple_str: str) -> str:
    """Parse simpleString() into a human-readable semantic detail."""
    clean = _strip_col_ids(simple_str)
    lower = node_name.lower()

    try:
        if "join" in lower:
            return _parse_join_detail(clean)
        if "filter" in lower:
            return _parse_filter_detail(clean)
        if "aggregate" in lower:
            return _parse_aggregate_detail(clean)
        if "scan" in lower or "datasource" in lower:
            return _parse_scan_detail(clean)
        if "sort" in lower and "merge" not in lower:
            return _parse_sort_detail(clean)
        if "exchange" in lower:
            return _parse_exchange_detail(clean)
        if node_name == "Project":
            return _parse_project_detail(clean)
    except Exception:
        pass

    # Fallback: return cleaned string if it adds info beyond the name
    if clean and clean != node_name and len(clean) > len(node_name) + 3:
        truncated = clean[:100] + ("..." if len(clean) > 100 else "")
        return _balance_parens(truncated)
    return ""


def _parse_join_detail(s: str) -> str:
    """Extract join type and keys from join simpleString."""
    # Pattern: BroadcastHashJoin [col_a], [col_b], Inner, BuildRight
    m = re.search(r"\[([^\]]+)\].*?\[([^\]]+)\].*?(Inner|Left|Right|LeftOuter|RightOuter|FullOuter|LeftSemi|LeftAnti|Cross)", s, re.IGNORECASE)
    if m:
        left_key = m.group(1).strip().split(",")[0].strip()
        join_type = m.group(3).lower().replace("outer", " outer").replace("semi", " semi").replace("anti", " anti")
        return f"{join_type} on {left_key}"
    # Simpler pattern: just extract join type
    for jtype in ("Inner", "LeftOuter", "RightOuter", "FullOuter", "LeftSemi", "LeftAnti", "Cross", "Left", "Right"):
        if jtype in s:
            return jtype.lower().replace("outer", " outer").replace("semi", " semi").replace("anti", " anti")
    return s[:80] if len(s) > 80 else s


def _parse_filter_detail(s: str) -> str:
    """Extract filter predicate."""
    # Pattern: Filter (predicate)
    m = re.search(r"Filter\s*\((.+)\)", s, re.DOTALL)
    if m:
        pred = _balance_parens(m.group(1).strip())
        # Clean up common Spark noise
        pred = pred.replace("isnotnull", "notnull")
        if len(pred) > 80:
            pred = pred[:77] + "..."
        return pred
    return s[:80] if len(s) > 80 else s


def _parse_aggregate_detail(s: str) -> str:
    """Extract aggregate keys and functions."""
    parts = []
    # Extract keys
    km = re.search(r"keys=\[([^\]]*)\]", s)
    if km and km.group(1).strip():
        keys = [k.strip() for k in km.group(1).split(",")]
        parts.append("by " + ", ".join(keys[:3]))
    # Extract functions
    fm = re.search(r"functions=\[([^\]]*)\]", s)
    if fm and fm.group(1).strip():
        # Extract just function names: count(1) → count, sum(col) → sum
        funcs = re.findall(r"(\w+)\(", fm.group(1))
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for f in funcs:
            if f not in seen and f not in ("cast", "coalesce", "knownfloatingpointnormalized"):
                seen.add(f)
                unique.append(f)
        if unique:
            parts.append(", ".join(unique[:4]) + ("..." if len(unique) > 4 else ""))
    return " | ".join(parts) if parts else ""


def _parse_scan_detail(s: str) -> str:
    """Extract table name and selected columns from scan."""
    # Pattern: BatchScan iceberg.dagger.table_name[col1, col2, ...]
    m = re.search(r"(?:Scan|BatchScan)\s+(?:iceberg\.dagger\.)?(\w+)\[([^\]]*)\]", s)
    if m:
        table = m.group(1)
        cols = [c.strip() for c in m.group(2).split(",")]
        col_str = ", ".join(cols[:4])
        if len(cols) > 4:
            col_str += f" +{len(cols) - 4}"
        return f"{table} [{col_str}]"
    # Just table name without columns
    m = re.search(r"(?:Scan|BatchScan)\s+(?:iceberg\.dagger\.)?(\w+)", s)
    if m:
        return m.group(1)
    return s[:80] if len(s) > 80 else s


def _parse_sort_detail(s: str) -> str:
    """Extract sort keys."""
    m = re.search(r"Sort\s*\[([^\]]+)\]", s)
    if m:
        keys = m.group(1)
        # Simplify "col ASC NULLS FIRST" → "col ASC"
        keys = re.sub(r"\s+NULLS\s+(FIRST|LAST)", "", keys)
        if len(keys) > 60:
            keys = keys[:57] + "..."
        return keys
    return ""


def _parse_exchange_detail(s: str) -> str:
    """Extract exchange type and partitioning."""
    # Pattern: Exchange hashpartitioning(col, 200)
    m = re.search(r"Exchange\s+(\w+)\(([^,)]+)(?:,\s*(\d+))?\)", s)
    if m:
        strategy = m.group(1).replace("partitioning", "")
        col = m.group(2).strip()
        parts = m.group(3)
        result = f"{strategy} on {col}"
        if parts:
            result += f" ({parts} parts)"
        return result
    # SinglePartition or RoundRobin
    m = re.search(r"Exchange\s+(\w+)", s)
    if m:
        return m.group(1).lower()
    return ""


def _parse_project_detail(s: str) -> str:
    """Extract output columns from Project."""
    m = re.search(r"Project\s*\[(.+)\]", s)
    if m:
        cols = [_balance_parens(c.strip().split(" AS ")[-1].strip()) for c in _split_top_level(m.group(1))]
        col_str = ", ".join(cols[:5])
        if len(cols) > 5:
            col_str += f" +{len(cols) - 5}"
        return col_str
    return ""


# ── Full (untruncated) detail parsers for expanded/modal view ────

def _parse_join_full(s: str) -> str:
    """Full join detail with all keys."""
    m = re.search(r"\[([^\]]+)\].*?\[([^\]]+)\].*?(Inner|Left|Right|LeftOuter|RightOuter|FullOuter|LeftSemi|LeftAnti|Cross)", s, re.IGNORECASE)
    if m:
        left_keys = m.group(1).strip()
        right_keys = m.group(2).strip()
        join_type = m.group(3).lower().replace("outer", " outer").replace("semi", " semi").replace("anti", " anti")
        return f"{join_type} on [{left_keys}] = [{right_keys}]"
    for jtype in ("Inner", "LeftOuter", "RightOuter", "FullOuter", "LeftSemi", "LeftAnti", "Cross", "Left", "Right"):
        if jtype in s:
            return jtype.lower().replace("outer", " outer").replace("semi", " semi").replace("anti", " anti")
    return s


def _parse_filter_full(s: str) -> str:
    """Full filter predicate without truncation."""
    m = re.search(r"Filter\s*\((.+)\)", s, re.DOTALL)
    if m:
        pred = _balance_parens(m.group(1).strip())
        pred = pred.replace("isnotnull", "notnull")
        return pred
    return s


def _parse_aggregate_full(s: str) -> str:
    """Full aggregate detail with all keys and functions."""
    parts = []
    km = re.search(r"keys=\[([^\]]*)\]", s)
    if km and km.group(1).strip():
        keys = [k.strip() for k in km.group(1).split(",")]
        parts.append("by " + ", ".join(keys))
    fm = re.search(r"functions=\[([^\]]*)\]", s)
    if fm and fm.group(1).strip():
        funcs = re.findall(r"(\w+)\(", fm.group(1))
        seen = set()
        unique = []
        for f in funcs:
            if f not in seen and f not in ("cast", "coalesce", "knownfloatingpointnormalized"):
                seen.add(f)
                unique.append(f)
        if unique:
            parts.append(", ".join(unique))
    return " | ".join(parts) if parts else ""


def _parse_scan_full(s: str) -> str:
    """Full scan detail with all columns."""
    m = re.search(r"(?:Scan|BatchScan)\s+(?:iceberg\.dagger\.)?(\w+)\[([^\]]*)\]", s)
    if m:
        table = m.group(1)
        cols = [c.strip() for c in m.group(2).split(",")]
        return f"{table} [{', '.join(cols)}]"
    m = re.search(r"(?:Scan|BatchScan)\s+(?:iceberg\.dagger\.)?(\w+)", s)
    if m:
        return m.group(1)
    return s


def _parse_sort_full(s: str) -> str:
    """Full sort keys without truncation."""
    m = re.search(r"Sort\s*\[([^\]]+)\]", s)
    if m:
        keys = m.group(1)
        keys = re.sub(r"\s+NULLS\s+(FIRST|LAST)", "", keys)
        return keys
    return ""


def _parse_project_full(s: str) -> str:
    """Full project columns without truncation."""
    m = re.search(r"Project\s*\[(.+)\]", s)
    if m:
        cols = [_balance_parens(c.strip().split(" AS ")[-1].strip()) for c in _split_top_level(m.group(1))]
        return ", ".join(cols)
    return ""


# ── Metric extraction ─────────────────────────────────────────────

_METRIC_DISPLAY = {
    "number of output rows": "rows",
    "numOutputRows": "rows",
    "number of files read": "files",
    "number of file splits read": "files",
    "number of result data files": "data files",
    "total data file size (bytes)": "data size",
    "total planning duration (ms)": "plan time",
    "metadata time": "metadata",
    "scan time": "scan time",
    "peak memory": "peak mem",
    "spill size": "spill",
    "avg hash probe bucket list iters": "avg probe",
    "time to build hash map": "build time",
    "time to update rows": "stream time",
    "data size": "data size",
    "number of partitions": "partitions",
    "shuffle records written": "shuffle rows",
    "sort time": "sort time",
    "time in aggregation build": "agg time",
    "shuffle bytes written": "shuffle bytes",
    "time to build": "build time",
    "build data size": "build size",
}

# Metrics that aren't useful to show in the frontend cards
_METRIC_SKIP = {
    "number of scanned data manifests",
    "number of skipped data manifests",
    "total data manifests",
    "total delete manifests",
    "number of scanned delete manifests",
    "number of skipped delete manifests",
    "number of result delete files",
    "total delete file size (bytes)",
}


def _clean_metric_value(raw: str) -> str:
    """Extract the total value from Spark's aggregated metric format.

    Spark returns aggregated metrics as:
      "total (min, med, max (stageId: taskId))\\n9 ms (0 ms, 9 ms, ...)"
    We extract just "9 ms" — the total value.
    """
    if not raw:
        return raw
    if "\n" in raw:
        # Multi-line aggregate: total is the first token on the second line
        second_line = raw.split("\n")[1].strip()
        # Take everything before the first "(" which starts the breakdown
        paren_idx = second_line.find("(")
        if paren_idx > 0:
            return second_line[:paren_idx].strip()
        return second_line
    return raw.strip()


def _is_zero_metric(val: str) -> bool:
    """Check if a metric value is effectively zero and should be hidden."""
    return val in ("0", "0.0", "0 B", "0.0 B", "0 ms", "0 ns", "0 s",
                   "0 KiB", "0 MiB", "0 GiB")


def _format_metric_value(metric_name: str, value: str) -> str:
    """Format metric value based on its type: rows, bytes, or time."""
    lower = metric_name.lower()
    # Try to parse as number
    try:
        num = int(value.replace(",", "").replace(" ", ""))
    except (ValueError, AttributeError):
        return value

    if "row" in lower or "records" in lower or "output" in lower or "partitions" in lower or "files" in lower:
        return _format_rows(str(num))
    if "size" in lower or "bytes" in lower or "memory" in lower:
        return _format_bytes(num)
    if "time" in lower or "duration" in lower:
        if "(ms)" in lower:
            # Value is already in milliseconds
            if num >= 60_000:
                return f"{num / 60_000:.1f}m"
            if num >= 1_000:
                return f"{num / 1_000:.1f}s"
            return f"{num}ms"
        return _format_time_ns(num)

    return _format_rows(str(num))


def _format_rows(value: str) -> str:
    """Format row count as human-readable (K/M)."""
    try:
        num = int(value.replace(",", ""))
    except (ValueError, AttributeError):
        return value
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def _format_bytes(num_bytes: int) -> str:
    """Format byte count as human-readable (KB/MB/GB)."""
    if num_bytes >= 1_073_741_824:
        return f"{num_bytes / 1_073_741_824:.1f} GB"
    if num_bytes >= 1_048_576:
        return f"{num_bytes / 1_048_576:.1f} MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024:.0f} KB"
    return f"{num_bytes} B"


def _format_time_ns(ns: int) -> str:
    """Format nanosecond timing as human-readable (ms/s/m)."""
    ms = ns / 1_000_000
    if ms >= 60_000:
        return f"{ms / 60_000:.1f}m"
    if ms >= 1_000:
        return f"{ms / 1_000:.1f}s"
    if ms >= 1:
        return f"{ms:.0f}ms"
    return f"{ns}ns"
