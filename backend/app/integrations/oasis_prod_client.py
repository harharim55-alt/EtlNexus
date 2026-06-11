"""Oasis Prod client — counts data consumption from the external ``observer`` table.

A consumption is one row in the observation table (env: ``OASIS_OBSERVER_TABLE``)
where ``storage_types`` equals ``OASIS_OBSERVER_STORAGE_TYPE`` (default ``iceberg``)
and the row's ``(data_source_name, data_name)`` match a pipeline's team + name.
``total_reads`` is the row count; ``unique_reads`` is the number of distinct days
(``ts``) on which the data was consumed. The table has no per-consumer column, so
no per-principal breakdown is produced.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)

# A bare SQL identifier — table names are interpolated (bind params can't name a
# table), so the env-provided name must be validated to prevent SQL injection.
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass
class UsageMetrics:
    unique_reads: int          # distinct days (ts) with at least one consumption
    total_reads: int           # total matching observation rows
    last_accessed_at: datetime | None


def _safe_table(name: str) -> str:
    if not _IDENT_RE.match(name):
        raise ValueError(f"Invalid observer table name (must be a plain SQL identifier): {name!r}")
    return name


class OasisProdClient:
    def __init__(self) -> None:
        self._engine = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._connected = False
        self._usage_query = None
        self._batch_query = None

    @property
    def is_configured(self) -> bool:
        return bool(settings.oasis_prod_database_url)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _build_url(self) -> str:
        """Inject username/password into the database URL if provided."""
        url = settings.oasis_prod_database_url
        if settings.oasis_prod_username:
            parsed = urlparse(url)
            netloc = f"{settings.oasis_prod_username}"
            if settings.oasis_prod_password:
                netloc += f":{settings.oasis_prod_password}"
            netloc += f"@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            url = urlunparse(parsed._replace(netloc=netloc))
        return url

    def _build_queries(self) -> None:
        """Build the SQL once, with the validated, env-provided table name."""
        table = _safe_table(settings.oasis_observer_table)

        # Single ETL: count matching consumption rows + distinct consumption days.
        self._usage_query = text(f"""
            SELECT
                COUNT(*) AS total_reads,
                COUNT(DISTINCT date_trunc('day', ts)) AS unique_reads,
                MAX(ts) AS last_accessed_at
            FROM {table}
            WHERE storage_types = :storage_type
              AND data_source_name = :source
              AND data_name = :name
              AND (:date_from::timestamptz IS NULL OR ts >= :date_from)
              AND (:date_to::timestamptz IS NULL OR ts <= :date_to)
        """)

        # Batch (downstream consumers): one aggregate row per (source, name).
        self._batch_query = text(f"""
            SELECT
                data_source_name,
                data_name,
                COUNT(*) AS total_reads,
                COUNT(DISTINCT date_trunc('day', ts)) AS unique_reads,
                MAX(ts) AS last_accessed_at
            FROM {table}
            WHERE storage_types = :storage_type
              AND (data_source_name, data_name) IN (
                  SELECT s, n FROM unnest(:sources::text[], :names::text[]) AS t(s, n)
              )
              AND (:date_from::timestamptz IS NULL OR ts >= :date_from)
              AND (:date_to::timestamptz IS NULL OR ts <= :date_to)
            GROUP BY data_source_name, data_name
        """)

    async def initialize(self) -> None:
        if not self.is_configured:
            logger.info("Oasis Prod DB not configured — usage metrics disabled")
            return
        try:
            self._build_queries()
            url = self._build_url()
            self._engine = create_async_engine(
                url,
                echo=False,
                pool_size=settings.oasis_prod_pool_size,
                max_overflow=settings.oasis_prod_max_overflow,
                pool_recycle=3600,
                pool_pre_ping=True,
            )
            self._session_factory = async_sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with self._session_factory() as session:
                await session.execute(text("SELECT 1"))
            self._connected = True
            logger.info(
                "Oasis Prod DB connected (observer table=%s, storage_types=%s)",
                settings.oasis_observer_table, settings.oasis_observer_storage_type,
            )
        except ValueError:
            logger.exception("Oasis Prod observer table misconfigured — metrics disabled")
            self._connected = False
        except ConnectionRefusedError:
            logger.warning("Oasis Prod DB connection refused — metrics disabled")
            self._connected = False
        except OSError as exc:
            logger.warning("Oasis Prod DB unreachable (%s) — metrics disabled", exc)
            self._connected = False
        except Exception:
            logger.exception("Unexpected error connecting to Oasis Prod DB")
            self._connected = False

    async def get_usage_metrics(
        self,
        data_source_name: str,
        data_name: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> UsageMetrics | None:
        if not self._connected or not self._session_factory:
            return None
        try:
            async with self._session_factory() as session:
                row = (await session.execute(
                    self._usage_query,
                    {
                        "storage_type": settings.oasis_observer_storage_type,
                        "source": data_source_name,
                        "name": data_name,
                        "date_from": date_from,
                        "date_to": date_to,
                    },
                )).one()
            return UsageMetrics(
                unique_reads=row.unique_reads or 0,
                total_reads=row.total_reads or 0,
                last_accessed_at=row.last_accessed_at,
            )
        except Exception:
            logger.exception("Failed to query Oasis Prod consumption for %s.%s", data_source_name, data_name)
            return None

    async def get_batch_usage_metrics(
        self,
        products: list[tuple[str, str]],
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, UsageMetrics]:
        """Fetch consumption counts for multiple data products in a single query.

        Args:
            products: list of (data_source_name, data_name) tuples
        Returns:
            dict keyed by "source.name" -> UsageMetrics
        """
        if not self._connected or not self._session_factory or not products:
            return {}
        try:
            sources = [p[0] for p in products]
            names = [p[1] for p in products]
            async with self._session_factory() as session:
                result = await session.execute(
                    self._batch_query,
                    {
                        "storage_type": settings.oasis_observer_storage_type,
                        "sources": sources,
                        "names": names,
                        "date_from": date_from,
                        "date_to": date_to,
                    },
                )
                rows = result.fetchall()

            metrics_map: dict[str, UsageMetrics] = {}
            for row in rows:
                key = f"{row.data_source_name}.{row.data_name}"
                metrics_map[key] = UsageMetrics(
                    unique_reads=row.unique_reads or 0,
                    total_reads=row.total_reads or 0,
                    last_accessed_at=row.last_accessed_at,
                )
            return metrics_map
        except Exception:
            logger.exception("Failed to batch query Oasis Prod consumption")
            return {}

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()
            self._connected = False
            logger.info("Oasis Prod DB connection closed")


oasis_prod_client = OasisProdClient()
