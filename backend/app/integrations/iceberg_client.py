"""Iceberg catalog client using PySpark to read table schemas."""

import logging
import re
from dataclasses import dataclass, field

from app.config import settings

_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z0-9_.]+$")

logger = logging.getLogger(__name__)


@dataclass
class IcebergTableSchema:
    table_name: str
    namespace: str
    fields: list[dict] = field(default_factory=list)  # [{"name": ..., "type": ...}]


def _validate_identifier(value: str, label: str) -> str:
    """Validate that a value is a safe Spark SQL identifier (alphanumeric, dots, underscores)."""
    if not _SAFE_IDENTIFIER.match(value):
        raise ValueError(f"Unsafe {label}: {value!r} — must match [a-zA-Z0-9_.]")
    return value


class IcebergClient:
    def __init__(self):
        self.catalog_uri = settings.iceberg_catalog_uri
        self.catalog_name = _validate_identifier(
            settings.iceberg_catalog_name, "iceberg_catalog_name"
        )
        # Store raw comma-separated prefixes; each is validated individually at query time
        self.namespace_prefix = settings.iceberg_namespace_prefix
        self._spark = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _get_spark(self):
        """Lazily create a SparkSession configured for the Iceberg catalog."""
        if self._spark is not None:
            return self._spark
        try:
            from pyspark.sql import SparkSession

            self._spark = (
                SparkSession.builder
                .appName("EtlNexus-CatalogSync")
                .master("local[1]")
                .config("spark.jars", "/app/jars/iceberg-spark-runtime.jar")
                .config(f"spark.sql.catalog.{self.catalog_name}", "org.apache.iceberg.spark.SparkCatalog")
                .config(f"spark.sql.catalog.{self.catalog_name}.type", "rest")
                .config(f"spark.sql.catalog.{self.catalog_name}.uri", self.catalog_uri)
                .config("spark.sql.extensions",
                        "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
                .config("spark.driver.memory", "512m")
                .config("spark.ui.enabled", "false")
                .getOrCreate()
            )
            self._spark.sparkContext.setLogLevel("WARN")
            self._connected = True
            logger.info("SparkSession created for Iceberg catalog at %s", self.catalog_uri)
        except (ImportError, RuntimeError, OSError) as e:
            logger.warning("Failed to create SparkSession: %s", e)
            self._connected = False
            self._spark = None
        return self._spark

    async def check_health(self) -> bool:
        """Check if we can create a Spark session and reach the catalog."""
        try:
            spark = self._get_spark()
            if spark is None:
                return False
            # Try listing namespaces
            spark.sql(f"SHOW NAMESPACES IN {self.catalog_name}").collect()
            self._connected = True
            return True
        except Exception as e:
            logger.warning("Iceberg health check failed: %s", e)
            self._connected = False
            return False

    def list_tables_in_namespace(self, namespace: str) -> list[str]:
        """List all tables in a given Iceberg namespace."""
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

    def get_table_schema(self, full_table_name: str) -> IcebergTableSchema | None:
        """Read schema from an Iceberg table using spark.table().schema.

        Args:
            full_table_name: Fully qualified name e.g. "iceberg.dagger.PortScanCollector"
        """
        spark = self._get_spark()
        if not spark:
            return None
        try:
            table_df = spark.table(full_table_name)
            spark_schema = table_df.schema

            fields = []
            for sf in spark_schema:
                fields.append({
                    "name": sf.name,
                    "type": sf.dataType.simpleString().upper(),
                })

            parts = full_table_name.split(".")
            table_name = parts[-1]
            namespace = ".".join(parts[1:-1]) if len(parts) > 2 else ""

            logger.info("Read schema for %s: %d fields", full_table_name, len(fields))
            self._connected = True
            return IcebergTableSchema(
                table_name=table_name,
                namespace=namespace,
                fields=fields,
            )
        except Exception as e:
            logger.warning("Failed to read schema for %s: %s", full_table_name, e)
            return None

    def get_all_schemas(self) -> list[IcebergTableSchema]:
        """Discover all tables under the configured team namespace prefixes and read their schemas."""
        spark = self._get_spark()
        if not spark:
            return []

        schemas = []
        prefixes = [p.strip() for p in self.namespace_prefix.split(",")]
        for prefix in prefixes:
            try:
                _validate_identifier(prefix, "namespace_prefix")
                # List tables under each configured team namespace
                tables = self.list_tables_in_namespace(prefix)
                for table_name in tables:
                    _validate_identifier(table_name, "table_name")
                    full_name = f"{self.catalog_name}.{prefix}.{table_name}"
                    schema = self.get_table_schema(full_name)
                    if schema:
                        schemas.append(schema)
            except Exception as e:
                logger.warning("Failed to discover schemas for namespace '%s': %s", prefix, e)

        logger.info("Discovered %d table schemas from configured team namespaces", len(schemas))
        return schemas

    def stop(self):
        """Stop the SparkSession."""
        if self._spark:
            try:
                self._spark.stop()
            except Exception:
                logger.debug("SparkSession stop error", exc_info=True)
            self._spark = None
            self._connected = False


iceberg_client = IcebergClient()
