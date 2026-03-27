"""Iceberg catalog client using PyIceberg to read table schemas."""

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
    """Validate that a value is a safe identifier (alphanumeric, dots, underscores)."""
    if not _SAFE_IDENTIFIER.match(value):
        raise ValueError(f"Unsafe {label}: {value!r} — must match [a-zA-Z0-9_.]")
    return value


class IcebergClient:
    def __init__(self):
        self.catalog_uri = settings.iceberg_catalog_uri
        self.catalog_name = _validate_identifier(
            settings.iceberg_catalog_name, "iceberg_catalog_name"
        )
        self.namespace_prefix = settings.iceberg_namespace_prefix
        self._catalog = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _get_catalog(self):
        """Lazily create a PyIceberg REST catalog connection."""
        if self._catalog is not None:
            return self._catalog
        try:
            from pyiceberg.catalog import load_catalog

            self._catalog = load_catalog(
                self.catalog_name,
                type="rest",
                uri=self.catalog_uri,
            )
            self._connected = True
            logger.info("PyIceberg catalog connected at %s", self.catalog_uri)
        except Exception as e:
            logger.warning("Failed to connect to Iceberg catalog: %s", e)
            self._connected = False
            self._catalog = None
        return self._catalog

    async def check_health(self) -> bool:
        """Check if we can reach the Iceberg catalog."""
        try:
            catalog = self._get_catalog()
            if catalog is None:
                return False
            catalog.list_namespaces()
            self._connected = True
            return True
        except Exception as e:
            logger.warning("Iceberg health check failed: %s", e)
            self._connected = False
            return False

    def list_tables_in_namespace(self, namespace: str) -> list[str]:
        """List all tables in a given Iceberg namespace."""
        _validate_identifier(namespace, "namespace")
        catalog = self._get_catalog()
        if not catalog:
            return []
        try:
            tables = catalog.list_tables(namespace)
            return [table_id[-1] for table_id in tables]
        except Exception as e:
            logger.warning("Failed to list tables in %s: %s", namespace, e)
            return []

    def get_table_schema(self, namespace: str, table_name: str) -> IcebergTableSchema | None:
        """Read schema from an Iceberg table using PyIceberg.

        Args:
            namespace: Namespace e.g. "dagger"
            table_name: Table name e.g. "PortScanCollector"
        """
        catalog = self._get_catalog()
        if not catalog:
            return None
        try:
            table = catalog.load_table(f"{namespace}.{table_name}")
            schema = table.schema()

            fields = []
            for iceberg_field in schema.fields:
                fields.append({
                    "name": iceberg_field.name,
                    "type": str(iceberg_field.field_type).upper(),
                })

            logger.info("Read schema for %s.%s: %d fields", namespace, table_name, len(fields))
            self._connected = True
            return IcebergTableSchema(
                table_name=table_name,
                namespace=namespace,
                fields=fields,
            )
        except Exception as e:
            logger.warning("Failed to read schema for %s.%s: %s", namespace, table_name, e)
            return None

    def get_all_schemas(self) -> list[IcebergTableSchema]:
        """Discover all tables under the configured team namespace prefixes and read their schemas."""
        catalog = self._get_catalog()
        if not catalog:
            return []

        schemas: list[IcebergTableSchema] = []
        prefixes = [p.strip() for p in self.namespace_prefix.split(",")]
        for prefix in prefixes:
            try:
                _validate_identifier(prefix, "namespace_prefix")
                tables = self.list_tables_in_namespace(prefix)
                for table_name in tables:
                    _validate_identifier(table_name, "table_name")
                    schema = self.get_table_schema(prefix, table_name)
                    if schema:
                        schemas.append(schema)
            except Exception as e:
                logger.warning("Failed to discover schemas for namespace '%s': %s", prefix, e)

        logger.info("Discovered %d table schemas from configured team namespaces", len(schemas))
        return schemas

    def stop(self):
        """Clean up catalog connection."""
        self._catalog = None
        self._connected = False


iceberg_client = IcebergClient()
