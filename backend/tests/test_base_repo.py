"""Tests for the shared repository apply_updates utility."""

from app.repositories.base import apply_updates


class FakeModel:
    """Simple class to simulate a SQLAlchemy model."""

    def __init__(self, name: str = "", value: int = 0, status: str = "active"):
        self.name = name
        self.value = value
        self.status = status


class TestApplyUpdates:
    def test_applies_all_matching_fields(self):
        model = FakeModel(name="old", value=1)
        apply_updates(model, {"name": "new", "value": 42})
        assert model.name == "new"
        assert model.value == 42

    def test_skips_fields_not_on_model(self):
        model = FakeModel(name="old")
        apply_updates(model, {"name": "new", "nonexistent_field": "ignored"})
        assert model.name == "new"
        assert not hasattr(model, "nonexistent_field")

    def test_exclude_keys_skips_specified_fields(self):
        model = FakeModel(name="old", value=1)
        apply_updates(model, {"name": "new", "value": 42}, exclude_keys={"name"})
        assert model.name == "old"  # unchanged
        assert model.value == 42

    def test_condition_fn_can_block_updates(self):
        model = FakeModel(name="old", value=1, status="locked")

        def skip_locked(m, key, val):
            # Don't update name when status is locked
            return not (key == "name" and m.status == "locked")

        apply_updates(model, {"name": "new", "value": 42}, condition_fn=skip_locked)
        assert model.name == "old"  # blocked by condition
        assert model.value == 42  # not blocked

    def test_empty_data_does_nothing(self):
        model = FakeModel(name="unchanged")
        apply_updates(model, {})
        assert model.name == "unchanged"

    def test_exclude_keys_and_condition_fn_combined(self):
        model = FakeModel(name="old", value=1, status="draft")

        def skip_status(m, key, val):
            return key != "status"

        apply_updates(
            model,
            {"name": "new", "value": 99, "status": "published"},
            exclude_keys={"value"},
            condition_fn=skip_status,
        )
        assert model.name == "new"
        assert model.value == 1  # excluded
        assert model.status == "draft"  # blocked by condition
