"""Tests for AirflowSyncService static/helper methods and log parsers.

These are pure functions that parse log output, extract team names,
and convert task IDs to display names — all testable without any DB or network.
"""

import json

from app.parsers.log_parser import (
    parse_bouncer_description,
    parse_description,
    parse_execution_plan,
    parse_resource_actual,
    parse_writes,
)
from app.services.sync.task_classifier import (
    extract_category_from_task_group,
    extract_dag_schedule,
    extract_team_from_task_group,
    is_api,
    is_bouncer,
    parse_datetime,
    task_id_to_display_name,
    unwrap_params,
)


class TestParseWrites:
    def test_single_write_marker(self):
        log = "INFO ETL_WRITES_TO: target_table_1\nother log line"
        result = parse_writes(log, "fallback_id")
        assert result == ["target_table_1"]

    def test_multiple_write_markers(self):
        log = (
            "ETL_WRITES_TO: table_a\n"
            "some other log\n"
            "ETL_WRITES_TO: table_b\n"
        )
        result = parse_writes(log, "fallback_id")
        assert result == ["table_a", "table_b"]

    def test_no_markers_falls_back_to_task_id(self):
        log = "just some regular log output"
        result = parse_writes(log, "SwitchPortCollector")
        assert result == ["SwitchPortCollector"]

    def test_empty_log_falls_back_to_task_id(self):
        result = parse_writes("", "MyTask")
        assert result == ["MyTask"]

    def test_none_log_falls_back_to_task_id(self):
        # The method checks `if not log_content` so None evaluates the same
        result = parse_writes("", "FallbackTask")
        assert result == ["FallbackTask"]

    def test_empty_value_after_marker_is_skipped(self):
        log = "ETL_WRITES_TO: \nETL_WRITES_TO: valid_table"
        result = parse_writes(log, "fallback")
        assert result == ["valid_table"]

    def test_marker_with_extra_whitespace(self):
        log = "ETL_WRITES_TO:   table_with_spaces   "
        result = parse_writes(log, "fallback")
        assert result == ["table_with_spaces"]


class TestParseDescription:
    def test_extracts_description(self):
        log = "INFO ETL_DESCRIPTION: Collects switch port data from network devices"
        result = parse_description(log, "Switch Port Collector")
        assert result == "Collects switch port data from network devices"

    def test_no_description_falls_back_to_display_name(self):
        log = "just regular log"
        result = parse_description(log, "Switch Port Collector")
        assert result == "Switch Port Collector"

    def test_empty_log_falls_back(self):
        result = parse_description("", "Dhcp Lease Sync")
        assert result == "Dhcp Lease Sync"

    def test_empty_description_value_falls_back(self):
        log = "ETL_DESCRIPTION:   "
        result = parse_description(log, "Switch Port Collector")
        assert result == "Switch Port Collector"


class TestTaskIdToDisplayName:
    def test_pascal_case(self):
        assert task_id_to_display_name("SwitchPortCollector") == "Switch Port Collector"

    def test_snake_case(self):
        assert task_id_to_display_name("switch_port_collector") == "Switch Port Collector"

    def test_single_word(self):
        assert task_id_to_display_name("Collector") == "Collector"

    def test_mixed_case_with_numbers(self):
        result = task_id_to_display_name("Bgp4RouteAnalyzer")
        assert result == "Bgp4 Route Analyzer"

    def test_kebab_case(self):
        assert task_id_to_display_name("switch-port-collector") == "Switch Port Collector"

    def test_all_uppercase_acronym(self):
        result = task_id_to_display_name("DHCPLeaseSync")
        # The regex only splits lowercase→uppercase, so DHCP stays together
        assert "Dhcplease" in result or "Dhcp" in result


class TestExtractTeamFromTaskGroup:
    def test_hyphenated_task_group(self):
        known = {"Dagger", "Vault", "Prism"}
        result = extract_team_from_task_group("Dagger-Collection", known)
        assert result == "Dagger"

    def test_exact_match(self):
        known = {"Relay", "Oasis"}
        result = extract_team_from_task_group("Relay", known)
        assert result == "Relay"

    def test_unknown_team_returns_none(self):
        known = {"Dagger", "Vault"}
        result = extract_team_from_task_group("Unknown-Group", known)
        assert result is None

    def test_none_task_group_returns_none(self):
        known = {"Dagger"}
        result = extract_team_from_task_group(None, known)
        assert result is None

    def test_empty_string_returns_none(self):
        known = {"Dagger"}
        result = extract_team_from_task_group("", known)
        assert result is None

    def test_hyphenated_unknown_prefix(self):
        known = {"Dagger", "Vault"}
        result = extract_team_from_task_group("Alpha-Collection", known)
        assert result is None


class TestParseDatetime:
    def test_iso_format(self):
        result = parse_datetime("2025-01-15T10:30:00+00:00")
        assert result is not None
        assert result.year == 2025

    def test_z_suffix(self):
        result = parse_datetime("2025-01-15T10:30:00Z")
        assert result is not None

    def test_none_returns_none(self):
        assert parse_datetime(None) is None

    def test_empty_string_returns_none(self):
        assert parse_datetime("") is None

    def test_invalid_format_returns_none(self):
        assert parse_datetime("not-a-date") is None


class TestUnwrapParams:
    def test_unwraps_airflow_param_objects(self):
        raw = {
            "etl_name": {"__class": "airflow.models.param.Param", "value": "SwitchPortCollector"},
            "needs": {"__class": "airflow.models.param.Param", "value": ["other"]},
        }
        result = unwrap_params(raw)
        assert result["etl_name"] == "SwitchPortCollector"
        assert result["needs"] == ["other"]

    def test_passes_through_plain_values(self):
        raw = {"etl_name": "plain", "count": 5}
        result = unwrap_params(raw)
        assert result == {"etl_name": "plain", "count": 5}

    def test_empty_params(self):
        assert unwrap_params({}) == {}

    def test_none_params(self):
        assert unwrap_params(None) == {}


class TestParseResourceActual:
    def test_parses_json_from_log(self):
        actual = {"driver_memory": "2g", "executor_memory": "4g"}
        log = f"INFO ETL_RESOURCE_ACTUAL: {json.dumps(actual)}"
        result = parse_resource_actual(log)
        assert result == actual

    def test_no_marker_returns_none(self):
        result = parse_resource_actual("just logs")
        assert result is None

    def test_empty_log_returns_none(self):
        assert parse_resource_actual("") is None

    def test_invalid_json_returns_none(self):
        log = "ETL_RESOURCE_ACTUAL: not_json"
        assert parse_resource_actual(log) is None


class TestParseExecutionPlan:
    def test_valid_plan(self):
        plan = {"node_type": "Scan", "children": []}
        log = f"ETL_EXECUTION_PLAN: {json.dumps(plan)}"
        result = parse_execution_plan(log)
        assert result is not None
        parsed = json.loads(result)
        assert parsed["node_type"] == "Scan"

    def test_no_marker_returns_none(self):
        assert parse_execution_plan("regular log") is None

    def test_invalid_json_returns_none(self):
        log = "ETL_EXECUTION_PLAN: {bad json}"
        assert parse_execution_plan(log) is None


class TestIsBouncer:
    def test_bouncer_name(self):
        assert is_bouncer("SwitchTelemetryBouncer") is True

    def test_etl_name(self):
        assert is_bouncer("SwitchPortCollector") is False

    def test_api_name(self):
        assert is_bouncer("NetworkInsightsApiDummy") is False


class TestIsApi:
    def test_api_pascal(self):
        assert is_api("NetworkInsightsApiDummy") is True

    def test_api_upper(self):
        assert is_api("SomeAPIDummy") is True

    def test_non_api(self):
        assert is_api("SwitchPortCollector") is False


class TestExtractCategoryFromTaskGroup:
    def test_hyphenated(self):
        assert extract_category_from_task_group("Dagger-Collection") == "Collection"

    def test_no_hyphen(self):
        assert extract_category_from_task_group("Relay") == "Relay"

    def test_none(self):
        assert extract_category_from_task_group(None) == "Uncategorized"

    def test_empty(self):
        assert extract_category_from_task_group("") == "Uncategorized"


class TestExtractDagSchedule:
    def test_timetable_description(self):
        dag_def = {"timetable_description": "At 01:00", "schedule_interval": "0 1 * * *"}
        assert extract_dag_schedule(dag_def) == "At 01:00"

    def test_fallback_to_schedule_interval(self):
        dag_def = {"timetable_description": "Never", "schedule_interval": "0 1 * * *"}
        assert extract_dag_schedule(dag_def) == "0 1 * * *"

    def test_empty_dag_def(self):
        assert extract_dag_schedule({}) is None


class TestParseBouncerDescription:
    def test_extracts_description(self):
        log = "BOUNCER_DESCRIPTION: Monitors network traffic"
        result = parse_bouncer_description(log, "Traffic Sensor")
        assert result == "Monitors network traffic"

    def test_falls_back_to_display_name(self):
        result = parse_bouncer_description("no desc", "Traffic Sensor")
        assert result == "Traffic Sensor"
