"""Tests for app.parsers.log_parser — log marker extraction utilities."""

import json

from app.parsers.log_parser import (
    parse_bouncer_description,
    parse_description,
    parse_execution_plan,
    parse_log_marker,
    parse_log_marker_json,
    parse_resource_actual,
    parse_writes,
)


class TestParseLogMarker:
    def test_extracts_value_after_marker(self):
        log = "INFO ETL_WRITES_TO: table_name\n"
        assert parse_log_marker(log, "ETL_WRITES_TO:") == "table_name"

    def test_returns_none_for_empty_log(self):
        assert parse_log_marker("", "MARKER:") is None
        assert parse_log_marker(None, "MARKER:") is None

    def test_returns_none_when_marker_not_found(self):
        assert parse_log_marker("just logs", "MARKER:") is None

    def test_returns_none_when_value_is_empty(self):
        assert parse_log_marker("MARKER:   ", "MARKER:") is None

    def test_strips_whitespace(self):
        assert parse_log_marker("MARKER:   value   ", "MARKER:") == "value"

    def test_returns_first_occurrence(self):
        log = "MARKER: first\nMARKER: second\n"
        assert parse_log_marker(log, "MARKER:") == "first"

    def test_handles_marker_with_prefix(self):
        log = "2025-01-01 INFO MARKER: value"
        assert parse_log_marker(log, "MARKER:") == "value"


class TestParseLogMarkerJson:
    def test_parses_valid_json(self):
        data = {"key": "value", "num": 42}
        log = f"MARKER: {json.dumps(data)}"
        assert parse_log_marker_json(log, "MARKER:") == data

    def test_returns_none_for_invalid_json(self):
        assert parse_log_marker_json("MARKER: not_json", "MARKER:") is None

    def test_returns_none_for_empty_log(self):
        assert parse_log_marker_json("", "MARKER:") is None

    def test_returns_none_when_marker_missing(self):
        assert parse_log_marker_json("no marker here", "MARKER:") is None


class TestParseWrites:
    def test_collects_multiple_write_targets(self):
        log = "ETL_WRITES_TO: table_a\nother\nETL_WRITES_TO: table_b\n"
        assert parse_writes(log, "fallback") == ["table_a", "table_b"]

    def test_falls_back_to_task_id_on_no_markers(self):
        assert parse_writes("just logs", "MyTask") == ["MyTask"]

    def test_falls_back_on_empty_log(self):
        assert parse_writes("", "MyTask") == ["MyTask"]

    def test_skips_empty_values(self):
        log = "ETL_WRITES_TO: \nETL_WRITES_TO: valid\n"
        assert parse_writes(log, "fallback") == ["valid"]


class TestParseDescription:
    def test_extracts_description(self):
        log = "ETL_DESCRIPTION: Collects data from network"
        assert parse_description(log, "fallback") == "Collects data from network"

    def test_falls_back_when_not_found(self):
        assert parse_description("no desc", "Fallback Name") == "Fallback Name"

    def test_falls_back_on_empty_log(self):
        assert parse_description("", "Fallback") == "Fallback"

    def test_falls_back_on_empty_value(self):
        assert parse_description("ETL_DESCRIPTION:   ", "Fallback") == "Fallback"


class TestParseBouncerDescription:
    def test_extracts_bouncer_description(self):
        log = "BOUNCER_DESCRIPTION: Monitors traffic"
        assert parse_bouncer_description(log, "fallback") == "Monitors traffic"

    def test_falls_back_when_not_found(self):
        assert parse_bouncer_description("no desc", "Fallback") == "Fallback"


class TestParseResourceActual:
    def test_parses_resource_json(self):
        actual = {"driver_memory": "2g", "executor_memory": "4g"}
        log = f"ETL_RESOURCE_ACTUAL: {json.dumps(actual)}"
        assert parse_resource_actual(log) == actual

    def test_returns_none_on_no_marker(self):
        assert parse_resource_actual("just logs") is None

    def test_returns_none_on_empty(self):
        assert parse_resource_actual("") is None

    def test_returns_none_on_invalid_json(self):
        assert parse_resource_actual("ETL_RESOURCE_ACTUAL: not_json") is None


class TestParseExecutionPlan:
    def test_returns_valid_json_string(self):
        plan = {"node_type": "Scan", "children": []}
        log = f"ETL_EXECUTION_PLAN: {json.dumps(plan)}"
        result = parse_execution_plan(log)
        assert result is not None
        assert json.loads(result) == plan

    def test_returns_none_on_no_marker(self):
        assert parse_execution_plan("regular log") is None

    def test_returns_none_on_invalid_json(self):
        assert parse_execution_plan("ETL_EXECUTION_PLAN: {bad}") is None

    def test_returns_none_on_empty_log(self):
        assert parse_execution_plan("") is None

    def test_handles_multiline_log(self):
        plan = {"type": "read"}
        log = f"line1\nline2\nETL_EXECUTION_PLAN: {json.dumps(plan)}\nline4"
        result = parse_execution_plan(log)
        assert result is not None
        assert json.loads(result)["type"] == "read"
