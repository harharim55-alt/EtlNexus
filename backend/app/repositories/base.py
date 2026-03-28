"""Shared repository utilities for upsert patterns."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def apply_updates(
    model: Any,
    data: dict[str, Any],
    *,
    exclude_keys: set[str] | None = None,
    condition_fn: Callable[[Any, str, Any], bool] | None = None,
) -> None:
    """Apply dict values to a SQLAlchemy model instance via setattr.

    Only keys that correspond to actual mapped table columns are applied.
    This prevents accidentally setting transient attributes, relationships,
    or arbitrary keys supplied from untrusted input.

    Args:
        model: SQLAlchemy model instance to update.
        data: Dict of field_name -> value to apply.
        exclude_keys: Field names to skip unconditionally.
        condition_fn: Optional callable(model, key, value) -> bool.
            If provided and returns False, that field is skipped.
    """
    skip = exclude_keys or set()
    # Build an allowlist of mapped column keys when available (SQLAlchemy models).
    table = getattr(model, "__table__", None)
    valid_columns: set[str] | None = {c.key for c in table.columns} if table is not None else None
    for key, value in data.items():
        if key in skip:
            continue
        if valid_columns is not None and key not in valid_columns:
            continue
        if valid_columns is None and not hasattr(model, key):
            continue
        if condition_fn and not condition_fn(model, key, value):
            continue
        setattr(model, key, value)


class UpsertMixin:
    """Mixin providing a generic get-or-create upsert for repositories with a ``self.session``.

    Subclasses must have a ``session`` attribute of type :class:`AsyncSession`.
    The :meth:`_upsert` helper looks up an existing row by ``lookup_kwargs``,
    applies ``data`` to it via :func:`apply_updates` when found, or creates a
    new instance when not found.
    """

    session: AsyncSession

    async def _upsert(
        self,
        model_cls: type,
        lookup_kwargs: dict[str, Any],
        data: dict[str, Any],
        *,
        exclude_keys: set[str] | None = None,
        condition_fn: Callable[[Any, str, Any], bool] | None = None,
    ) -> Any:
        """Get-or-create upsert for a SQLAlchemy model.

        Args:
            model_cls: The ORM model class to query and instantiate.
            lookup_kwargs: Keyword arguments passed to ``filter_by`` for the
                existence check.
            data: Full dict of field values to apply on update, or use as
                constructor kwargs on insert.
            exclude_keys: Field names to skip during the update phase.
            condition_fn: Optional callable(model, key, value) -> bool passed
                through to :func:`apply_updates`.

        Returns:
            The updated or newly-created model instance, flushed to the session.
        """
        stmt = select(model_cls).filter_by(**lookup_kwargs)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            apply_updates(
                existing,
                data,
                exclude_keys=exclude_keys,
                condition_fn=condition_fn,
            )
            return existing
        obj = model_cls(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj
