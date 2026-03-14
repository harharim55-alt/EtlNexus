"""Shared repository utilities for upsert patterns."""

from typing import Any


def apply_updates(
    model: Any,
    data: dict[str, Any],
    *,
    exclude_keys: set[str] | None = None,
    condition_fn: Any | None = None,
) -> None:
    """Apply dict values to a SQLAlchemy model instance via setattr.

    Args:
        model: SQLAlchemy model instance to update.
        data: Dict of field_name -> value to apply.
        exclude_keys: Field names to skip unconditionally.
        condition_fn: Optional callable(model, key, value) -> bool.
            If provided and returns False, that field is skipped.
    """
    skip = exclude_keys or set()
    for key, value in data.items():
        if key in skip:
            continue
        if not hasattr(model, key):
            continue
        if condition_fn and not condition_fn(model, key, value):
            continue
        setattr(model, key, value)
