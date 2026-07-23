"""Table service.

Table *existence* comes from the external, read-only ``iceberg_table_metrics``
table (namespace + name only). A single table's *schema* is read live from Spark
Connect on demand — only when a user actually opens that table — and cached
briefly so repeated views don't hammer Spark.
"""

import asyncio
import logging

from app.cache import table_schema_cache
from app.config import render_table_consume_snippet
from app.integrations.spark_connect_client import spark_connect_client
from app.repositories.iceberg_metrics_repo import IcebergMetricsRepository
from app.schemas.table import TableColumn, TableListItem, TableSchema

logger = logging.getLogger(__name__)


class TableService:
    def __init__(self, metrics_repo: IcebergMetricsRepository):
        self.metrics_repo = metrics_repo

    async def list_tables(self, team_names: list[str] | None = None, q: str | None = None) -> list[TableListItem]:
        """All catalog tables (namespace + name), filterable by team and name."""
        pairs = await self.metrics_repo.list_tables(team_names=team_names, q=q)
        return [TableListItem(namespace=ns, table_name=tbl) for ns, tbl in pairs]

    async def list_namespaces(self) -> list[str]:
        """Distinct namespaces present in the catalog (used for the team filter)."""
        return await self.metrics_repo.list_namespaces()

    async def get_table_schema(self, namespace: str, table_name: str) -> TableSchema | None:
        """Read a single table's schema live from Spark Connect (short-TTL cached)."""
        cache_key = f"{namespace}.{table_name}"
        cached = table_schema_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            spark_schema = await asyncio.to_thread(spark_connect_client.get_table_schema, namespace, table_name)
        except ValueError:
            # Unsafe identifier — treat as not found.
            logger.warning("Rejected unsafe table identifier %s.%s", namespace, table_name)
            return None
        if spark_schema is None:
            return None

        columns = [
            TableColumn(name=f["name"], data_type=f.get("type"), ordinal_position=i)
            for i, f in enumerate(spark_schema.fields)
        ]
        result = TableSchema(
            namespace=namespace,
            table_name=table_name,
            columns=columns,
            consume_snippet=render_table_consume_snippet(namespace, table_name),
        )
        table_schema_cache.set(cache_key, result)
        return result
