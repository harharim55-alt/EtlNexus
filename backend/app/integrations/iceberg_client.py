"""Iceberg catalog client using PySpark to read table schemas."""

import logging
from dataclasses import dataclass, field

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class IcebergTableSchema:
    table_name: str
    namespace: str
    fields: list[dict] = field(default_factory=list)  # [{"name": ..., "type": ...}]


class IcebergClient:
    def __init__(self):
        self.catalog_uri = settings.iceberg_catalog_uri
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
                .config("spark.jars.packages",
                        "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.1")
                .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
                .config("spark.sql.catalog.iceberg.type", "rest")
                .config("spark.sql.catalog.iceberg.uri", self.catalog_uri)
                .config("spark.sql.extensions",
                        "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
                .config("spark.driver.memory", "512m")
                .config("spark.ui.enabled", "false")
                .getOrCreate()
            )
            self._spark.sparkContext.setLogLevel("WARN")
            self._connected = True
            logger.info("SparkSession created for Iceberg catalog at %s", self.catalog_uri)
        except Exception as e:
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
            spark.sql("SHOW NAMESPACES IN iceberg").collect()
            self._connected = True
            return True
        except Exception as e:
            logger.warning("Iceberg health check failed: %s", e)
            self._connected = False
            return False

    def list_tables_in_namespace(self, namespace: str) -> list[str]:
        """List all tables in a given Iceberg namespace."""
        spark = self._get_spark()
        if not spark:
            return []
        try:
            rows = spark.sql(f"SHOW TABLES IN iceberg.{namespace}").collect()
            return [row["tableName"] for row in rows]
        except Exception as e:
            logger.warning("Failed to list tables in %s: %s", namespace, e)
            return []

    def get_table_schema(self, full_table_name: str) -> IcebergTableSchema | None:
        """Read schema from an Iceberg table using spark.table().schema.

        Args:
            full_table_name: Fully qualified name e.g. "iceberg.catalog.iceberg.dagger.my_table"
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

    def get_all_dagger_schemas(self) -> list[IcebergTableSchema]:
        """Discover all tables under the configured namespace prefix and read their schemas."""
        spark = self._get_spark()
        if not spark:
            return []

        schemas = []
        try:
            # List tables under the dagger namespace
            tables = self.list_tables_in_namespace(self.namespace_prefix)
            for table_name in tables:
                full_name = f"iceberg.{self.namespace_prefix}.{table_name}"
                schema = self.get_table_schema(full_name)
                if schema:
                    schemas.append(schema)
        except Exception as e:
            logger.warning("Failed to discover dagger schemas: %s", e)

        logger.info("Discovered %d table schemas from Iceberg catalog", len(schemas))
        return schemas

    def stop(self):
        """Stop the SparkSession."""
        if self._spark:
            try:
                self._spark.stop()
            except Exception:
                pass
            self._spark = None
            self._connected = False


iceberg_client = IcebergClient()
