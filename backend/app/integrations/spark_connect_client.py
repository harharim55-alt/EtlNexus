"""Spark Connect client — reads a single Iceberg table's schema on demand.

The backend connects to a Spark Connect server (``sc://host:port``) and reads a
table's schema with Spark SQL when a user opens that table. There is no catalog
mirroring or bulk discovery — which tables exist is known from the external
``iceberg_table_metrics`` table, and schemas are fetched live per request.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field

from app.config import settings

_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z0-9_.]+$")

logger = logging.getLogger(__name__)


@dataclass
class SparkTableSchema:
    table_name: str
    namespace: str
    fields: list[dict] = field(default_factory=list)  # [{"name": ..., "type": ...}]


def _validate_identifier(value: str, label: str) -> str:
    """Validate that a value is a safe identifier (alphanumeric, dots, underscores)."""
    if not _SAFE_IDENTIFIER.match(value):
        raise ValueError(f"Unsafe {label}: {value!r} — must match [a-zA-Z0-9_.]")
    return value


class SparkConnectClient:
    def __init__(self):
        self.remote_url = settings.spark_connect_url
        self.catalog_name = _validate_identifier(settings.spark_catalog_name, "spark_catalog_name")
        self._spark = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _get_spark(self):
        """Lazily create a Spark Connect session bound to the remote server."""
        if self._spark is not None:
            return self._spark
        try:
            from pyspark.sql import SparkSession

            self._spark = SparkSession.builder.remote(self.remote_url).getOrCreate()
            self._connected = True
            logger.info("Spark Connect session created at %s", self.remote_url)
        except Exception as e:
            logger.warning("Failed to create Spark Connect session: %s", e)
            self._connected = False
            self._spark = None
        return self._spark

    async def check_health(self) -> bool:
        """Check if we can reach the Spark Connect server."""
        return await asyncio.to_thread(self._check_health_sync)

    def _check_health_sync(self) -> bool:
        """Synchronous health check (runs in thread pool)."""
        try:
            spark = self._get_spark()
            if spark is None:
                return False
            spark.sql("SELECT 1").collect()
            self._connected = True
            return True
        except Exception as e:
            logger.warning("Spark Connect health check failed: %s", e)
            self._connected = False
            return False

    def get_table_schema(self, namespace: str, table_name: str) -> SparkTableSchema | None:
        """Read a single Iceberg table's schema via Spark Connect.

        Args:
            namespace: Namespace e.g. "vault"
            table_name: Table name e.g. "logins"

        Raises:
            ValueError: if either identifier contains unsafe characters.
        """
        _validate_identifier(namespace, "namespace")
        _validate_identifier(table_name, "table_name")
        spark = self._get_spark()
        if not spark:
            return None
        try:
            fqn = f"{self.catalog_name}.{namespace}.{table_name}"
            struct = spark.table(fqn).schema

            fields = [
                {
                    "name": struct_field.name,
                    "type": struct_field.dataType.simpleString().upper(),
                }
                for struct_field in struct.fields
            ]

            logger.info("Read schema for %s.%s: %d fields", namespace, table_name, len(fields))
            self._connected = True
            return SparkTableSchema(
                table_name=table_name,
                namespace=namespace,
                fields=fields,
            )
        except Exception as e:
            logger.warning("Failed to read schema for %s.%s: %s", namespace, table_name, e)
            return None

    def stop(self):
        """Clean up the Spark Connect session."""
        if self._spark is not None:
            try:
                self._spark.stop()
            except Exception as e:
                logger.warning("Error stopping Spark Connect session: %s", e)
        self._spark = None
        self._connected = False


spark_connect_client = SparkConnectClient()
