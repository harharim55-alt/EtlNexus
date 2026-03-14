"""Task classification and metadata extraction helpers.

Pure functions for classifying Airflow tasks, extracting metadata from
task groups and DAG definitions, and converting task IDs to display names.
"""

import re
from datetime import datetime


def is_bouncer(task_id: str) -> bool:
    """Check if a task_id represents a bouncer (data ingestion root task)."""
    return "Bouncer" in task_id


def is_api(task_id: str) -> bool:
    """Check if a task_id represents an API task (skip writes_to lineage)."""
    return "Api" in task_id or "API" in task_id


def task_id_to_display_name(task_id: str) -> str:
    """Convert task_id to display name.

    Handles both PascalCase and snake_case:
      'SwitchPortCollector' -> 'Switch Port Collector'
      'switch_port_collector' -> 'Switch Port Collector'
    """
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", task_id)
    return spaced.replace("_", " ").replace("-", " ").strip().title()


def extract_team_from_task_group(
    task_group: str | None, known_teams: set[str]
) -> str | None:
    """Extract team name from task_group.

    Supports:
      'Dagger-Collection' -> 'Dagger'  (split on first '-')
      'Relay'             -> 'Relay'   (exact match)
    """
    if not task_group:
        return None
    if "-" in task_group:
        team_part = task_group.split("-", 1)[0]
        if team_part in known_teams:
            return team_part
        return None
    if task_group in known_teams:
        return task_group
    return None


def extract_category_from_task_group(task_group: str | None) -> str:
    """Extract category from TaskGroup name.

    'Dagger-Collection' -> 'Collection'
    'Relay'             -> 'Relay'
    None                -> 'Uncategorized'
    """
    if not task_group:
        return "Uncategorized"
    if "-" in task_group:
        return task_group.split("-", 1)[1]
    return task_group


def extract_dag_schedule(dag_def: dict) -> str | None:
    """Extract schedule from DAG definition.

    Prefers timetable_description, falls back to schedule_interval.
    """
    schedule = dag_def.get("timetable_description")
    if schedule and schedule != "Never":
        return schedule
    return dag_def.get("schedule_interval") or None


def parse_datetime(date_str: str | None) -> datetime | None:
    """Parse ISO datetime string, handling Z suffix."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def unwrap_params(raw_params: dict) -> dict:
    """Unwrap Airflow Param objects to plain values.

    Airflow REST API serialises params as:
      {"key": {"__class": "airflow.models.param.Param", "value": X}}
    This extracts the inner 'value' for each key.
    """
    if not raw_params:
        return {}
    result: dict = {}
    for key, val in raw_params.items():
        if isinstance(val, dict) and "value" in val:
            result[key] = val["value"]
        else:
            result[key] = val
    return result
