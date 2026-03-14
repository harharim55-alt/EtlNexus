"""Log marker parsers for Airflow task log output.

Each ETL/bouncer task emits structured markers in its log that encode
metadata (writes_to targets, descriptions, resource actuals, execution
plans).  These parsers extract that data from raw log text.
"""

import json
import logging

logger = logging.getLogger(__name__)


def parse_log_marker(log_content: str, marker: str) -> str | None:
    """Extract the first value after *marker* in log lines.

    Returns the trimmed text after the marker, or ``None`` if not found.
    """
    if not log_content:
        return None
    for line in log_content.splitlines():
        if marker in line:
            parts = line.split(marker, 1)
            if len(parts) == 2:
                value = parts[1].strip()
                if value:
                    return value
    return None


def parse_log_marker_json(log_content: str, marker: str) -> dict | None:
    """Extract and JSON-parse the first value after *marker* in log lines."""
    raw = parse_log_marker(log_content, marker)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        logger.debug("Failed to parse JSON from marker %s", marker)
        return None


def parse_writes(log_content: str, task_id: str) -> list[str]:
    """Parse ETL_WRITES_TO lines from a task's log output."""
    if not log_content:
        return [task_id]
    tables: list[str] = []
    for line in log_content.splitlines():
        if "ETL_WRITES_TO:" in line:
            parts = line.split("ETL_WRITES_TO:", 1)
            if len(parts) == 2:
                table = parts[1].strip()
                if table:
                    tables.append(table)
    return tables if tables else [task_id]


def parse_description(log_content: str, fallback: str) -> str:
    """Parse ETL_DESCRIPTION line from a task's log output."""
    value = parse_log_marker(log_content, "ETL_DESCRIPTION:")
    return value if value else fallback


def parse_bouncer_description(log_content: str, fallback: str) -> str:
    """Parse BOUNCER_DESCRIPTION line from a bouncer task's log output."""
    value = parse_log_marker(log_content, "BOUNCER_DESCRIPTION:")
    return value if value else fallback


def parse_resource_actual(log_content: str) -> dict | None:
    """Parse ETL_RESOURCE_ACTUAL JSON from task log."""
    return parse_log_marker_json(log_content, "ETL_RESOURCE_ACTUAL:")


def parse_execution_plan(log_content: str) -> str | None:
    """Extract execution plan JSON string from task log.

    Returns the raw JSON string (not parsed) so it can be stored directly.
    """
    raw = parse_log_marker(log_content, "ETL_EXECUTION_PLAN:")
    if raw is None:
        return None
    try:
        json.loads(raw)  # validate it's valid JSON
        return raw
    except (json.JSONDecodeError, ValueError):
        return None
