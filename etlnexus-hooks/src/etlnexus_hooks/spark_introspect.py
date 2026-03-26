"""Spark introspection — extract execution plans, metrics, and write targets.

All functions accept a SparkSession and return structured data suitable for
EtlNexus log markers.  Failures are caught and logged — they never break
the ETL itself.
"""

import json
import logging
import re
from contextlib import contextmanager

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Write capture — intercept Iceberg table writes during load()
# ═══════════════════════════════════════════════════════════════════════

@contextmanager
def capture_writes(spark):
    """Context manager that records Iceberg table names written via writeTo().

    Wraps the SparkSession so that any ``writeTo("iceberg.ns.table")`` call
    is captured.  Yields a list that is populated as writes happen.

    Usage::

        with capture_writes(spark) as tables:
            etl.load()
        # tables == ["iceberg.dagger.PortScanCollector", ...]
    """
    written_tables: list[str] = []
    original_writeTo = None

    try:
        from pyspark.sql import DataFrame

        original_writeTo = DataFrame.writeTo

        def _intercepted_writeTo(df_self, table):
            written_tables.append(table)
            return original_writeTo(df_self, table)

        DataFrame.writeTo = _intercepted_writeTo
    except Exception:
        logger.debug("Could not install write interceptor", exc_info=True)

    try:
        yield written_tables
    finally:
        if original_writeTo is not None:
            try:
                from pyspark.sql import DataFrame
                DataFrame.writeTo = original_writeTo
            except Exception:
                pass


def parse_table_name(full_table: str) -> str:
    """Extract the short table name from ``iceberg.namespace.TableName``.

    Returns the last dot-separated segment, or the original string if
    there are no dots.
    """
    parts = full_table.split(".")
    return parts[-1] if parts else full_table


# ═══════════════════════════════════════════════════════════════════════
# Metrics collection — Spark resource usage after run()
# ═══════════════════════════════════════════════════════════════════════

def collect_metrics(spark) -> dict | None:
    """Collect resource usage metrics from the SparkSession.

    Tries sparkMeasure first for detailed metrics, then falls back to
    reading from Spark's internal StatusStore.  Returns ``None`` if no
    metrics could be collected.
    """
    try:
        metrics = _collect_from_status_store(spark)
        if metrics:
            return metrics
    except Exception:
        logger.debug("Could not collect metrics from StatusStore", exc_info=True)

    return None


def _collect_from_status_store(spark) -> dict | None:
    """Read aggregate metrics from the Spark StatusStore."""
    store = spark._jsparkSession.sharedState().statusStore()
    exec_list = store.executionsList()
    if exec_list.isEmpty():
        return None

    last_exec = exec_list.last()
    exec_id = last_exec.executionId()

    metric_values = store.executionMetrics(exec_id)
    acc_map: dict[int, str] = {}
    it = metric_values.iterator()
    while it.hasNext():
        pair = it.next()
        acc_map[int(pair._1())] = str(pair._2())

    if not acc_map:
        return None

    # Extract the plan graph to read per-node metrics
    graph = store.planGraph(exec_id)
    all_nodes = graph.allNodes()

    total_rows = 0
    total_input_bytes = 0
    total_output_bytes = 0
    total_shuffle_read = 0
    total_shuffle_write = 0

    for i in range(all_nodes.size()):
        n = all_nodes.apply(i)
        metric_seq = n.metrics()
        for j in range(metric_seq.size()):
            m = metric_seq.apply(j)
            name = str(m.name()).lower()
            mid = int(m.accumulatorId())
            if mid not in acc_map:
                continue
            try:
                raw = _clean_metric_value(acc_map[mid])
                val = int(raw.replace(",", "").replace(" ", ""))
            except (ValueError, AttributeError):
                continue

            if "output rows" in name or "numoutputrows" in name:
                total_rows += val
            elif "input" in name and "bytes" in name and "size" in name:
                total_input_bytes += val
            elif "data file size" in name:
                total_output_bytes += val
            elif "shuffle" in name and "read" in name and "bytes" in name:
                total_shuffle_read += val
            elif "shuffle" in name and "writ" in name and "bytes" in name:
                total_shuffle_write += val

    return {
        "total_output_rows": total_rows,
        "input_bytes": total_input_bytes,
        "output_bytes": total_output_bytes,
        "shuffle_read_bytes": total_shuffle_read,
        "shuffle_write_bytes": total_shuffle_write,
        "metrics_source": "status_store",
    }


# ═══════════════════════════════════════════════════════════════════════
# Execution plan extraction — build tree from Spark's plan graph
# ═══════════════════════════════════════════════════════════════════════

def extract_execution_plan(spark, result_df=None) -> dict | None:
    """Extract the Spark execution plan as a JSON-serialisable tree.

    Uses the StatusStore's plan graph (same data source as the Spark UI).
    Falls back to the initial plan (pre-AQE) if the graph is trivial
    (collapsed to LocalTableScan).

    Args:
        spark: Active SparkSession.
        result_df: Optional result DataFrame for initial-plan fallback.

    Returns:
        Plan tree dict or ``None`` if extraction fails.
    """
    try:
        # Flush the async listener bus so the AppStatusStore has complete data
        try:
            spark.sparkContext._jsc.sc().listenerBus().waitUntilEmpty(10000)
        except Exception:
            pass

        plan_tree = _build_tree_from_graph(spark)
        graph_nodes = _count_nodes(plan_tree) if plan_tree else 0

        # If AQE collapsed the plan, try building from the initial plan
        if plan_tree and graph_nodes <= 3 and result_df is not None:
            initial_tree = _build_tree_from_initial_plan(spark, result_df)
            if initial_tree and _count_nodes(initial_tree) > graph_nodes:
                plan_tree = initial_tree

        return plan_tree
    except Exception:
        logger.debug("Could not extract execution plan", exc_info=True)
        return None


def _count_nodes(tree: dict) -> int:
    """Count total nodes in a plan tree dict."""
    return 1 + sum(_count_nodes(c) for c in tree.get("children", []))


def _build_tree_from_graph(spark) -> dict | None:
    """Build execution plan tree from the status store's plan graph.

    Uses ``planGraph(execId)`` for the graph structure and
    ``executionMetrics(execId)`` for accumulator values.
    """
    store = spark._jsparkSession.sharedState().statusStore()
    exec_list = store.executionsList()
    if exec_list.isEmpty():
        return None

    last_exec = exec_list.last()
    exec_id = last_exec.executionId()

    # Get accumulator values: Map[Long, String]
    metric_values = store.executionMetrics(exec_id)
    acc_map: dict[int, str] = {}
    it = metric_values.iterator()
    while it.hasNext():
        pair = it.next()
        acc_map[int(pair._1())] = str(pair._2())

    graph = store.planGraph(exec_id)
    all_nodes = graph.allNodes()
    edges = graph.edges()

    if all_nodes.size() == 0:
        return None

    node_map = {}
    for i in range(all_nodes.size()):
        n = all_nodes.apply(i)
        node_map[int(n.id())] = n

    children_map: dict[int, list[int]] = {}
    child_ids = set()
    for i in range(edges.size()):
        e = edges.apply(i)
        from_id = int(e.fromId())
        to_id = int(e.toId())
        children_map.setdefault(to_id, []).append(from_id)
        child_ids.add(from_id)

    root_ids = [nid for nid in node_map if nid not in child_ids]
    if not root_ids:
        return None

    counter = [0]

    def build_node(nid: int) -> dict | None:
        if nid not in node_map:
            return None
        n = node_map[nid]
        desc = str(n.desc())
        first_line = desc.split("\n")[0].strip()
        node_name = first_line.split("(")[0].split("[")[0].strip().split(" ")[0]

        if node_name in _SKIP_NODES:
            child_results = []
            for cid in children_map.get(nid, []):
                cr = build_node(cid)
                if cr:
                    child_results.append(cr)
            if len(child_results) == 1:
                return child_results[0]
            if child_results:
                counter[0] += 1
                return {
                    "id": counter[0], "name": node_name, "type": "transform",
                    "detail": "", "full_detail": "", "metrics": {},
                    "children": child_results,
                }
            return None

        clean_desc = _strip_col_ids(first_line)
        node_type = _classify_node(node_name)
        detail = _extract_detail(node_name, clean_desc)
        full_detail = _extract_full_detail(node_name, clean_desc)

        metrics = {}
        metric_seq = n.metrics()
        for j in range(metric_seq.size()):
            m = metric_seq.apply(j)
            name = str(m.name())
            if name in _METRIC_SKIP:
                continue
            mid = int(m.accumulatorId())
            if mid in acc_map:
                val = _clean_metric_value(acc_map[mid])
                if not val or _is_zero_metric(val):
                    continue
                display_key = _METRIC_DISPLAY.get(name, name)
                metrics[display_key] = _format_metric_value(name, val)

        child_results = []
        for cid in children_map.get(nid, []):
            cr = build_node(cid)
            if cr:
                child_results.append(cr)

        counter[0] += 1
        return {
            "id": counter[0],
            "name": _clean_node_name(node_name),
            "type": node_type,
            "detail": detail,
            "full_detail": full_detail,
            "metrics": metrics,
            "children": child_results,
        }

    for rid in root_ids:
        result = build_node(rid)
        if result:
            return result
    return None


def _build_tree_from_initial_plan(spark, result_df) -> dict | None:
    """Build plan tree from the initial (pre-AQE) plan via SparkPlanInfo.

    Fallback when AQE collapses a complex plan into LocalTableScan.
    Metrics won't be available (different accumulator ID space).
    """
    try:
        plan = result_df._jdf.queryExecution().executedPlan()
        if str(plan.nodeName()) == "AdaptiveSparkPlan":
            initial = plan.initialPlan()
        else:
            initial = plan

        SparkPlanInfo = spark._jvm.org.apache.spark.sql.execution.SparkPlanInfo
        SparkPlanGraph = spark._jvm.org.apache.spark.sql.execution.ui.SparkPlanGraph
        info = SparkPlanInfo.fromSparkPlan(initial)
        graph = SparkPlanGraph.apply(info)

        all_nodes = graph.allNodes()
        edges = graph.edges()

        if all_nodes.size() == 0:
            return None

        node_map = {}
        for i in range(all_nodes.size()):
            n = all_nodes.apply(i)
            node_map[int(n.id())] = n

        children_map: dict[int, list[int]] = {}
        child_ids = set()
        for i in range(edges.size()):
            e = edges.apply(i)
            from_id = int(e.fromId())
            to_id = int(e.toId())
            children_map.setdefault(to_id, []).append(from_id)
            child_ids.add(from_id)

        root_ids = [nid for nid in node_map if nid not in child_ids]
        if not root_ids:
            return None

        counter = [0]

        def build_node(nid: int) -> dict | None:
            if nid not in node_map:
                return None
            n = node_map[nid]
            desc = str(n.desc())
            first_line = desc.split("\n")[0].strip()
            node_name = first_line.split("(")[0].split("[")[0].strip().split(" ")[0]

            if node_name in _SKIP_NODES:
                child_results = []
                for cid in children_map.get(nid, []):
                    cr = build_node(cid)
                    if cr:
                        child_results.append(cr)
                if len(child_results) == 1:
                    return child_results[0]
                if child_results:
                    counter[0] += 1
                    return {
                        "id": counter[0], "name": node_name, "type": "transform",
                        "detail": "", "full_detail": "", "metrics": {},
                        "children": child_results,
                    }
                return None

            clean_desc = _strip_col_ids(first_line)
            node_type = _classify_node(node_name)
            detail = _extract_detail(node_name, clean_desc)
            full_detail = _extract_full_detail(node_name, clean_desc)

            child_results = []
            for cid in children_map.get(nid, []):
                cr = build_node(cid)
                if cr:
                    child_results.append(cr)

            counter[0] += 1
            return {
                "id": counter[0],
                "name": _clean_node_name(node_name),
                "type": node_type,
                "detail": detail,
                "full_detail": full_detail,
                "metrics": {},
                "children": child_results,
            }

        for rid in root_ids:
            result = build_node(rid)
            if result:
                return result
        return None
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════
# Node classification and detail extraction helpers
# ═══════════════════════════════════════════════════════════════════════

_SKIP_NODES = {
    "AdaptiveSparkPlan", "WholeStageCodegen", "InputAdapter",
    "ColumnarToRow", "BroadcastQueryStage", "ShuffleQueryStage",
    "CommandResult", "Execute", "OverwritePartitionsDynamic", "WriteFiles",
}

_COL_ID_RE = re.compile(r"#\d+[L]?")


def _strip_col_ids(s: str) -> str:
    return _COL_ID_RE.sub("", s)


def _classify_node(name: str) -> str:
    lower = name.lower()
    if "scan" in lower or "datasource" in lower:
        return "read"
    if "write" in lower or "insert" in lower or "overwrite" in lower or "append" in lower:
        return "write"
    if "join" in lower or "exchange" in lower or "sort" in lower or "shuffle" in lower:
        return "shuffle"
    return "transform"


def _clean_node_name(name: str) -> str:
    for prefix in ("Batched",):
        if name.startswith(prefix) and len(name) > len(prefix):
            name = name[len(prefix):]
    return name


# ── Detail extraction ─────────────────────────────────────────────────

def _split_top_level(s: str, sep: str = ",") -> list[str]:
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
    opens = s.count("(")
    closes = s.count(")")
    if opens > closes:
        s += ")" * (opens - closes)
    elif closes > opens:
        s = "(" * (closes - opens) + s
    return s


def _extract_top_brackets(s: str) -> list[str]:
    result = []
    depth = 0
    current: list[str] = []
    in_bracket = False
    for ch in s:
        if ch == "[" and depth == 0:
            in_bracket = True
            depth = 1
            current = []
        elif ch == "[":
            depth += 1
            current.append(ch)
        elif ch == "]" and depth == 1:
            depth = 0
            in_bracket = False
            result.append("".join(current))
        elif ch == "]":
            depth -= 1
            current.append(ch)
        elif in_bracket:
            current.append(ch)
    return result


def _extract_detail(node_name: str, simple_str: str) -> str:
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
        if lower == "window":
            return _parse_window_detail(clean)
        if "sort" in lower and "merge" not in lower:
            return _parse_sort_detail(clean)
        if "exchange" in lower:
            return _parse_exchange_detail(clean)
        if node_name == "Project":
            return _parse_project_detail(clean)
        if "limit" in lower or lower == "takeorderedandproject":
            return _parse_limit_detail(clean)
        if lower in ("union", "expand", "generate", "coalesce"):
            return _parse_simple_node_detail(node_name, clean)
    except Exception:
        pass
    if clean and clean != node_name and len(clean) > len(node_name) + 3:
        truncated = clean[:100] + ("..." if len(clean) > 100 else "")
        return _balance_parens(truncated)
    return ""


def _extract_full_detail(node_name: str, simple_str: str) -> str:
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
        if lower == "window":
            return _parse_window_full(clean)
        if "sort" in lower and "merge" not in lower:
            return _parse_sort_full(clean)
        if "exchange" in lower:
            return _parse_exchange_detail(clean)
        if node_name == "Project":
            return _parse_project_full(clean)
        if "limit" in lower or lower == "takeorderedandproject":
            return _parse_limit_detail(clean)
        if lower in ("union", "expand", "generate", "coalesce"):
            return _parse_simple_node_detail(node_name, clean)
    except Exception:
        pass
    if clean and clean != node_name and len(clean) > len(node_name) + 3:
        return _balance_parens(clean)
    return ""


# ── Node-type detail parsers ──────────────────────────────────────────

def _parse_join_detail(s: str) -> str:
    m = re.search(
        r"\[([^\]]+)\].*?\[([^\]]+)\].*?(Inner|Left|Right|LeftOuter|RightOuter|FullOuter|LeftSemi|LeftAnti|Cross)",
        s, re.IGNORECASE,
    )
    if m:
        left_key = m.group(1).strip().split(",")[0].strip()
        join_type = m.group(3).lower().replace("outer", " outer").replace("semi", " semi").replace("anti", " anti")
        return f"{join_type} on {left_key}"
    for jtype in ("Inner", "LeftOuter", "RightOuter", "FullOuter", "LeftSemi", "LeftAnti", "Cross", "Left", "Right"):
        if jtype in s:
            return jtype.lower().replace("outer", " outer").replace("semi", " semi").replace("anti", " anti")
    return s[:80] if len(s) > 80 else s


def _parse_join_full(s: str) -> str:
    m = re.search(
        r"\[([^\]]+)\].*?\[([^\]]+)\].*?(Inner|Left|Right|LeftOuter|RightOuter|FullOuter|LeftSemi|LeftAnti|Cross)",
        s, re.IGNORECASE,
    )
    if m:
        left_keys = m.group(1).strip()
        right_keys = m.group(2).strip()
        join_type = m.group(3).lower().replace("outer", " outer").replace("semi", " semi").replace("anti", " anti")
        return f"{join_type} on [{left_keys}] = [{right_keys}]"
    for jtype in ("Inner", "LeftOuter", "RightOuter", "FullOuter", "LeftSemi", "LeftAnti", "Cross", "Left", "Right"):
        if jtype in s:
            return jtype.lower().replace("outer", " outer").replace("semi", " semi").replace("anti", " anti")
    return s


def _parse_filter_detail(s: str) -> str:
    m = re.search(r"Filter\s*\((.+)\)", s, re.DOTALL)
    if m:
        pred = _balance_parens(m.group(1).strip())
        pred = pred.replace("isnotnull", "notnull")
        if len(pred) > 80:
            pred = pred[:77] + "..."
        return pred
    return s[:80] if len(s) > 80 else s


def _parse_filter_full(s: str) -> str:
    m = re.search(r"Filter\s*\((.+)\)", s, re.DOTALL)
    if m:
        pred = _balance_parens(m.group(1).strip())
        pred = pred.replace("isnotnull", "notnull")
        return pred
    return s


def _parse_aggregate_detail(s: str) -> str:
    parts = []
    km = re.search(r"keys=\[([^\]]*)\]", s)
    if km and km.group(1).strip():
        keys = [k.strip() for k in km.group(1).split(",")]
        parts.append("by " + ", ".join(keys[:3]))
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
            parts.append(", ".join(unique[:4]) + ("..." if len(unique) > 4 else ""))
    return " | ".join(parts) if parts else ""


def _parse_aggregate_full(s: str) -> str:
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


def _parse_scan_detail(s: str) -> str:
    m = re.search(r"(?:Scan|BatchScan)\s+iceberg\.(\w+)\.(\w+)\[([^\]]*)\]", s)
    if m:
        table = m.group(2)
        cols = [c.strip() for c in m.group(3).split(",")]
        col_str = ", ".join(cols[:4])
        if len(cols) > 4:
            col_str += f" +{len(cols) - 4}"
        return f"{table} [{col_str}]"
    m = re.search(r"(?:Scan|BatchScan)\s+(\w+)\[([^\]]*)\]", s)
    if m:
        table = m.group(1)
        cols = [c.strip() for c in m.group(2).split(",")]
        col_str = ", ".join(cols[:4])
        if len(cols) > 4:
            col_str += f" +{len(cols) - 4}"
        return f"{table} [{col_str}]"
    m = re.search(r"(?:Scan|BatchScan)\s+(?:iceberg\.\w+\.)?(\w+)", s)
    if m:
        return m.group(1)
    return s[:80] if len(s) > 80 else s


def _parse_scan_full(s: str) -> str:
    parts = []
    m = re.search(r"(?:Scan|BatchScan)\s+iceberg\.(\w+)\.(\w+)\[([^\]]*)\]", s)
    if m:
        namespace, table, cols_str = m.group(1), m.group(2), m.group(3)
        cols = [c.strip() for c in cols_str.split(",")]
        parts.append(f"{table} [{', '.join(cols)}]")
        parts.append(f"namespace: {namespace}")
    else:
        m = re.search(r"(?:Scan|BatchScan)\s+(\w+)\[([^\]]*)\]", s)
        if m:
            cols = [c.strip() for c in m.group(2).split(",")]
            parts.append(f"{m.group(1)} [{', '.join(cols)}]")
        else:
            m = re.search(r"(?:Scan|BatchScan)\s+(?:iceberg\.\w+\.)?(\w+)", s)
            if m:
                parts.append(m.group(1))
            else:
                return s
    fm = re.search(r"\[filters=([^\]]*)\]", s)
    if fm:
        raw_filters = fm.group(1).strip()
        raw_filters = re.sub(r",?\s*groupedBy=\s*$", "", raw_filters).strip()
        if raw_filters:
            parts.append(f"filters: {raw_filters}")
    return "\n".join(parts) if parts else s


def _parse_sort_detail(s: str) -> str:
    m = re.search(r"Sort\s*\[([^\]]+)\]", s)
    if m:
        keys = m.group(1)
        keys = re.sub(r"\s+NULLS\s+(FIRST|LAST)", "", keys)
        if len(keys) > 60:
            keys = keys[:57] + "..."
        return keys
    return ""


def _parse_sort_full(s: str) -> str:
    m = re.search(r"Sort\s*\[([^\]]+)\]", s)
    if m:
        keys = m.group(1)
        keys = re.sub(r"\s+NULLS\s+(FIRST|LAST)", "", keys)
        return keys
    return ""


def _parse_exchange_detail(s: str) -> str:
    m = re.search(r"Exchange\s+(\w+)\(([^,)]+)(?:,\s*(\d+))?\)", s)
    if m:
        strategy = m.group(1).replace("partitioning", "")
        col = m.group(2).strip()
        parts = m.group(3)
        result = f"{strategy} on {col}"
        if parts:
            result += f" ({parts} parts)"
        return result
    m = re.search(r"Exchange\s+(\w+)", s)
    if m:
        return m.group(1).lower()
    return ""


def _parse_window_detail(s: str) -> str:
    brackets = _extract_top_brackets(s)
    parts = []
    if len(brackets) >= 2 and brackets[1].strip():
        cols = [c.strip() for c in brackets[1].split(",")]
        parts.append("partition by " + ", ".join(cols[:3]) + ("..." if len(cols) > 3 else ""))
    if len(brackets) >= 3 and brackets[2].strip():
        order = brackets[2]
        order = re.sub(r"\s+NULLS\s+(FIRST|LAST)", "", order)
        cols = [c.strip() for c in order.split(",")]
        parts.append("order by " + ", ".join(cols[:3]) + ("..." if len(cols) > 3 else ""))
    if len(brackets) >= 1 and brackets[0].strip():
        funcs = re.findall(r"(\w+)\(", brackets[0])
        seen = set()
        unique = []
        for f in funcs:
            if f not in seen and f not in (
                "windowspecdefinition", "specifiedwindowframe", "cast", "coalesce",
                "RowFrame", "RangeFrame", "unboundedpreceding", "unboundedfollowing",
                "currentrow", "knownfloatingpointnormalized",
            ):
                seen.add(f)
                unique.append(f)
        if unique:
            parts.append(", ".join(unique[:4]) + ("..." if len(unique) > 4 else ""))
    return " | ".join(parts) if parts else ""


def _parse_window_full(s: str) -> str:
    brackets = _extract_top_brackets(s)
    parts = []
    if len(brackets) >= 2 and brackets[1].strip():
        cols = [c.strip() for c in brackets[1].split(",")]
        parts.append("partition by " + ", ".join(cols))
    if len(brackets) >= 3 and brackets[2].strip():
        order = brackets[2]
        order = re.sub(r"\s+NULLS\s+(FIRST|LAST)", "", order)
        parts.append("order by " + order)
    if len(brackets) >= 1 and brackets[0].strip():
        funcs = re.findall(r"(\w+)\(", brackets[0])
        seen = set()
        unique = []
        for f in funcs:
            if f not in seen and f not in (
                "windowspecdefinition", "specifiedwindowframe", "cast", "coalesce",
                "RowFrame", "RangeFrame", "unboundedpreceding", "unboundedfollowing",
                "currentrow", "knownfloatingpointnormalized",
            ):
                seen.add(f)
                unique.append(f)
        if unique:
            parts.append(", ".join(unique))
    return " | ".join(parts) if parts else ""


def _parse_project_detail(s: str) -> str:
    m = re.search(r"Project\s*\[(.+)\]", s)
    if m:
        cols = [_balance_parens(c.strip().split(" AS ")[-1].strip()) for c in _split_top_level(m.group(1))]
        col_str = ", ".join(cols[:5])
        if len(cols) > 5:
            col_str += f" +{len(cols) - 5}"
        return col_str
    return ""


def _parse_project_full(s: str) -> str:
    m = re.search(r"Project\s*\[(.+)\]", s)
    if m:
        cols = [_balance_parens(c.strip().split(" AS ")[-1].strip()) for c in _split_top_level(m.group(1))]
        return ", ".join(cols)
    return ""


def _parse_limit_detail(s: str) -> str:
    m = re.search(r"limit[=\s]+(\d+)", s, re.IGNORECASE)
    limit_val = m.group(1) if m else ""
    sm = re.search(r"\[([^\]]*(?:ASC|DESC)[^\]]*)\]", s)
    sort_part = ""
    if sm:
        keys = sm.group(1)
        keys = re.sub(r"\s+NULLS\s+(FIRST|LAST)", "", keys)
        sort_part = keys
    parts = []
    if limit_val:
        parts.append(f"limit {limit_val}")
    if sort_part:
        parts.append(f"order by {sort_part}")
    return " | ".join(parts) if parts else ""


def _parse_simple_node_detail(node_name: str, s: str) -> str:
    lower = node_name.lower()
    if lower == "union":
        return "union"
    if lower == "coalesce":
        m = re.search(r"Coalesce\s+(\d+)", s)
        if m:
            return f"{m.group(1)} partitions"
    if lower == "expand":
        groups = re.findall(r"\[([^\[\]]+)\]", s)
        if groups:
            output_cols = [c.strip() for c in groups[-1].split(",") if c.strip() and c.strip() != "null"]
            n_groups = len(groups) - 1
            parts = []
            if n_groups > 0:
                parts.append(f"{n_groups} groups")
            if output_cols:
                col_str = ", ".join(output_cols[:4])
                if len(output_cols) > 4:
                    col_str += f" +{len(output_cols) - 4}"
                parts.append(col_str)
            return " | ".join(parts) if parts else ""
    if lower == "generate":
        m = re.search(r"Generator\s+(\w+)", s) or re.search(r"Generate\s+(\w+)", s)
        if m:
            return m.group(1)
    clean = s.replace(node_name, "").strip()
    if clean and len(clean) > 3:
        return clean[:80] + ("..." if len(clean) > 80 else "")
    return ""


# ── Metric formatting ─────────────────────────────────────────────────

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
    if not raw:
        return raw
    if "\n" in raw:
        second_line = raw.split("\n")[1].strip()
        paren_idx = second_line.find("(")
        if paren_idx > 0:
            return second_line[:paren_idx].strip()
        return second_line
    return raw.strip()


def _is_zero_metric(val: str) -> bool:
    return val in ("0", "0.0", "0 B", "0.0 B", "0 ms", "0 ns", "0 s",
                   "0 KiB", "0 MiB", "0 GiB")


def _format_metric_value(metric_name: str, value: str) -> str:
    lower = metric_name.lower()
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
            if num >= 60_000:
                return f"{num / 60_000:.1f}m"
            if num >= 1_000:
                return f"{num / 1_000:.1f}s"
            return f"{num}ms"
        return _format_time_ns(num)
    return _format_rows(str(num))


def _format_rows(value: str) -> str:
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
    if num_bytes >= 1_073_741_824:
        return f"{num_bytes / 1_073_741_824:.1f} GB"
    if num_bytes >= 1_048_576:
        return f"{num_bytes / 1_048_576:.1f} MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024:.0f} KB"
    return f"{num_bytes} B"


def _format_time_ns(ns: int) -> str:
    ms = ns / 1_000_000
    if ms >= 60_000:
        return f"{ms / 60_000:.1f}m"
    if ms >= 1_000:
        return f"{ms / 1_000:.1f}s"
    if ms >= 1:
        return f"{ms:.0f}ms"
    return f"{ns}ns"
