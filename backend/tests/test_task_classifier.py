"""Tests for sync/task_classifier — pure classification and metadata helpers."""

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


class TestIsBouncer:
    def test_bouncer_suffix(self):
        assert is_bouncer("SwitchTelemetryBouncer") is True

    def test_bouncer_in_middle(self):
        assert is_bouncer("MyBouncerTask") is True

    def test_not_bouncer(self):
        assert is_bouncer("PortScanCollector") is False

    def test_case_sensitive(self):
        assert is_bouncer("switchbouncer") is False
        # "Bouncer" substring match is case-sensitive — capital B required
        assert is_bouncer("switchBouncer") is True  # contains "Bouncer"


class TestIsApi:
    def test_api_pascal(self):
        assert is_api("NetworkIntelApiDummy") is True

    def test_api_upper(self):
        assert is_api("SomeAPIDummy") is True

    def test_not_api(self):
        assert is_api("PortScanCollector") is False

    def test_case_matters(self):
        assert is_api("apiEndpoint") is False


class TestTaskIdToDisplayName:
    def test_pascal_case(self):
        assert task_id_to_display_name("PortScanCollector") == "Port Scan Collector"

    def test_snake_case(self):
        assert task_id_to_display_name("port_scan_collector") == "Port Scan Collector"

    def test_kebab_case(self):
        assert task_id_to_display_name("port-scan-collector") == "Port Scan Collector"

    def test_single_word(self):
        assert task_id_to_display_name("Collector") == "Collector"

    def test_with_numbers(self):
        assert task_id_to_display_name("Bgp4RouteAnalyzer") == "Bgp4 Route Analyzer"

    def test_empty_string(self):
        assert task_id_to_display_name("") == ""


class TestExtractTeamFromTaskGroup:
    KNOWN = {"Dagger", "Vault", "Prism", "Relay", "Oasis"}

    def test_hyphenated(self):
        assert extract_team_from_task_group("Dagger-Collection", self.KNOWN) == "Dagger"

    def test_exact_match(self):
        assert extract_team_from_task_group("Relay", self.KNOWN) == "Relay"

    def test_unknown_returns_none(self):
        assert extract_team_from_task_group("Unknown-Group", self.KNOWN) is None

    def test_none_returns_none(self):
        assert extract_team_from_task_group(None, self.KNOWN) is None

    def test_empty_string_returns_none(self):
        assert extract_team_from_task_group("", self.KNOWN) is None


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
    def test_prefers_timetable_description(self):
        dag = {"timetable_description": "At 01:00", "schedule_interval": "0 1 * * *"}
        assert extract_dag_schedule(dag) == "At 01:00"

    def test_skips_never_timetable(self):
        dag = {"timetable_description": "Never", "schedule_interval": "0 1 * * *"}
        assert extract_dag_schedule(dag) == "0 1 * * *"

    def test_returns_none_when_empty(self):
        assert extract_dag_schedule({}) is None

    def test_returns_none_for_none_values(self):
        dag = {"timetable_description": None, "schedule_interval": None}
        assert extract_dag_schedule(dag) is None


class TestParseDatetime:
    def test_iso_format(self):
        result = parse_datetime("2025-01-15T10:30:00+00:00")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1

    def test_z_suffix(self):
        result = parse_datetime("2025-01-15T10:30:00Z")
        assert result is not None

    def test_none(self):
        assert parse_datetime(None) is None

    def test_empty(self):
        assert parse_datetime("") is None

    def test_invalid(self):
        assert parse_datetime("not-a-date") is None


class TestUnwrapParams:
    def test_unwraps_airflow_params(self):
        raw = {
            "etl_name": {"__class": "airflow.models.param.Param", "value": "Test"},
            "needs": {"__class": "airflow.models.param.Param", "value": ["a", "b"]},
        }
        result = unwrap_params(raw)
        assert result["etl_name"] == "Test"
        assert result["needs"] == ["a", "b"]

    def test_passes_through_plain_values(self):
        raw = {"key": "plain", "num": 42}
        assert unwrap_params(raw) == {"key": "plain", "num": 42}

    def test_empty(self):
        assert unwrap_params({}) == {}

    def test_none(self):
        assert unwrap_params(None) == {}

    def test_mixed(self):
        raw = {
            "wrapped": {"__class": "Param", "value": "inner"},
            "plain": "outer",
        }
        result = unwrap_params(raw)
        assert result["wrapped"] == "inner"
        assert result["plain"] == "outer"
