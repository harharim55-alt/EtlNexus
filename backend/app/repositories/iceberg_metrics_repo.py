"""Read-only repository over the external ``iceberg_table_metrics`` table.

This table is owned by an outside system and already exists in the database; we
only SELECT its ``db_name`` (namespace) and ``tbl_name`` (table) columns to learn
which Iceberg tables exist. We NEVER write to it.

Listings are restricted to a single snapshot date — the ``date`` column equals
(today - ICEBERG_METRICS_DAY_OFFSET days), evaluated DB-side via CURRENT_DATE.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.iceberg_metrics import iceberg_table_metrics

_DB = iceberg_table_metrics.c.db_name
_TBL = iceberg_table_metrics.c.tbl_name
_DATE = iceberg_table_metrics.c.date


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _on_target_date():
    """Rows whose `date` is (today - configured offset), computed by the DB.

    DB-side CURRENT_DATE keeps it consistent with the snapshot's own clock and
    avoids the backend/DB timezone-skew that a Python-computed date would have.
    """
    return (func.current_date() - settings.iceberg_metrics_day_offset) == _DATE


class IcebergMetricsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_tables(self, team_names: list[str] | None = None, q: str | None = None) -> list[tuple[str, str]]:
        """Distinct (db_name, tbl_name) pairs for the target date, with optional
        namespace + name filters.

        Namespace matching is case-insensitive (e.g. team "Vault" matches db_name
        "vault").
        """
        stmt = select(_DB, _TBL).where(_DB.isnot(None), _TBL.isnot(None), _on_target_date()).distinct()
        if team_names:
            stmt = stmt.where(func.lower(_DB).in_([t.lower() for t in team_names]))
        if q:
            stmt = stmt.where(_TBL.ilike(f"%{_escape_like(q)}%", escape="\\"))
        stmt = stmt.order_by(_DB, _TBL)
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def list_namespaces(self) -> list[str]:
        """Distinct namespaces (db_name) present for the target date."""
        stmt = select(_DB).where(_DB.isnot(None), _on_target_date()).distinct().order_by(_DB)
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def table_exists(self, namespace: str, table_name: str) -> bool:
        """Whether (namespace, table) appears for the target date (case-insensitive namespace)."""
        stmt = (
            select(func.count())
            .select_from(iceberg_table_metrics)
            .where(func.lower(_DB) == namespace.lower(), table_name == _TBL, _on_target_date())
        )
        return (await self.session.execute(stmt)).scalar_one() > 0
