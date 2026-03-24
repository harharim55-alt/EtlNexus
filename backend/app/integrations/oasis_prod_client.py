"""Oasis Prod client — queries external observation tables for data product usage metrics."""

import logging
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ConsumerMetric:
    principal: str
    total_reads: int
    last_accessed_at: datetime | None


@dataclass
class UsageMetrics:
    unique_reads: int
    total_reads: int
    consumers: list[ConsumerMetric]


_USAGE_QUERY = text("""
SELECT
    principal,
    COUNT(timestamp) as total_reads,
    MAX(timestamp) as last_accessed_at
FROM (
    SELECT principal, timestamp FROM data_interpaction_observeration_hdfs
    WHERE data_source_name = :source AND data_name = :name
      AND (:date_from::timestamptz IS NULL OR timestamp >= :date_from)
      AND (:date_to::timestamptz IS NULL OR timestamp <= :date_to)
    UNION ALL
    SELECT principal, timestamp FROM data_interpaction_observeration_iceberg
    WHERE data_source_name = :source AND data_name = :name
      AND (:date_from::timestamptz IS NULL OR timestamp >= :date_from)
      AND (:date_to::timestamptz IS NULL OR timestamp <= :date_to)
) combined
GROUP BY principal
ORDER BY total_reads DESC
""")

_BATCH_USAGE_QUERY = text("""
SELECT
    data_source_name,
    data_name,
    COUNT(DISTINCT principal) as unique_reads,
    COUNT(timestamp) as total_reads,
    MAX(timestamp) as last_accessed_at
FROM (
    SELECT data_source_name, data_name, principal, timestamp
    FROM data_interpaction_observeration_hdfs
    WHERE (data_source_name, data_name) IN (SELECT s, n FROM unnest(:sources::text[], :names::text[]) AS t(s, n))
      AND (:date_from::timestamptz IS NULL OR timestamp >= :date_from)
      AND (:date_to::timestamptz IS NULL OR timestamp <= :date_to)
    UNION ALL
    SELECT data_source_name, data_name, principal, timestamp
    FROM data_interpaction_observeration_iceberg
    WHERE (data_source_name, data_name) IN (SELECT s, n FROM unnest(:sources::text[], :names::text[]) AS t(s, n))
      AND (:date_from::timestamptz IS NULL OR timestamp >= :date_from)
      AND (:date_to::timestamptz IS NULL OR timestamp <= :date_to)
) combined
GROUP BY data_source_name, data_name
""")


class OasisProdClient:
    def __init__(self) -> None:
        self._engine = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._connected = False

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

    async def initialize(self) -> None:
        if not self.is_configured:
            logger.info("Oasis Prod DB not configured — usage metrics disabled")
            return
        try:
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
            logger.info("Oasis Prod DB connected")
        except Exception:
            logger.exception("Failed to connect to Oasis Prod DB")
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
                result = await session.execute(
                    _USAGE_QUERY,
                    {
                        "source": data_source_name,
                        "name": data_name,
                        "date_from": date_from,
                        "date_to": date_to,
                    },
                )
                rows = result.fetchall()

            consumers = [
                ConsumerMetric(
                    principal=row.principal,
                    total_reads=row.total_reads,
                    last_accessed_at=row.last_accessed_at,
                )
                for row in rows
            ]
            unique_reads = len(consumers)
            total_reads = sum(c.total_reads for c in consumers)
            return UsageMetrics(
                unique_reads=unique_reads,
                total_reads=total_reads,
                consumers=consumers,
            )
        except Exception:
            logger.exception("Failed to query Oasis Prod usage metrics for %s.%s", data_source_name, data_name)
            return None

    async def get_batch_usage_metrics(
        self,
        products: list[tuple[str, str]],
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, UsageMetrics]:
        """Fetch aggregated metrics for multiple data products in a single query.

        Args:
            products: list of (data_source_name, data_name) tuples
        Returns:
            dict keyed by "source.name" -> UsageMetrics (aggregate only, no per-principal breakdown)
        """
        if not self._connected or not self._session_factory or not products:
            return {}
        try:
            sources = [p[0] for p in products]
            names = [p[1] for p in products]
            async with self._session_factory() as session:
                result = await session.execute(
                    _BATCH_USAGE_QUERY,
                    {
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
                    unique_reads=row.unique_reads,
                    total_reads=row.total_reads,
                    consumers=[],
                )
            return metrics_map
        except Exception:
            logger.exception("Failed to batch query Oasis Prod usage metrics")
            return {}

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()
            self._connected = False
            logger.info("Oasis Prod DB connection closed")


oasis_prod_client = OasisProdClient()
