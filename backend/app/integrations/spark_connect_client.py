"""Spark Connect client — reads Iceberg table schemas via a remote Spark Connect server.

Replaces the previous PyIceberg REST-catalog client. Tables are still Iceberg
format; only the access path changed. The backend connects to a Spark Connect
server (``sc://host:port``) and reads schemas with Spark SQL, so it needs no JVM
or catalog credentials of its own — the server owns the Iceberg catalog config.
"""

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
        self.catalog_name = _validate_identifier(
            settings.spark_catalog_name, "spark_catalog_name"
        )
        self.namespace_prefix = settings.spark_namespace_prefix
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
        import asyncio
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

    def list_tables_in_namespace(self, namespace: str) -> list[str]:
        """List all tables in a given namespace of the configured Spark catalog."""
        _validate_identifier(namespace, "namespace")
        spark = self._get_spark()
        if not spark:
            return []
        try:
            rows = spark.sql(f"SHOW TABLES IN {self.catalog_name}.{namespace}").collect()
            return [row["tableName"] for row in rows]
        except Exception as e:
            logger.warning("Failed to list tables in %s: %s", namespace, e)
            return []

    def get_table_schema(self, namespace: str, table_name: str) -> SparkTableSchema | None:
        """Read schema from an Iceberg table via Spark Connect.

        Args:
            namespace: Namespace e.g. "dagger"
            table_name: Table name e.g. "PortScanCollector"
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

    def get_all_schemas(self) -> list[SparkTableSchema]:
        """Discover all tables under the configured team namespace prefixes and read their schemas."""
        spark = self._get_spark()
        if not spark:
            return []

        schemas: list[SparkTableSchema] = []
        prefixes = [p.strip() for p in self.namespace_prefix.split(",")]
        for prefix in prefixes:
            try:
                _validate_identifier(prefix, "namespace_prefix")
                tables = self.list_tables_in_namespace(prefix)
                for table_name in tables:
                    schema = self.get_table_schema(prefix, table_name)
                    if schema:
                        schemas.append(schema)
            except Exception as e:
                logger.warning("Failed to discover schemas for namespace '%s': %s", prefix, e)

        logger.info("Discovered %d table schemas from configured team namespaces", len(schemas))
        return schemas

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
