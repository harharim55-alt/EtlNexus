"""Table service — lists Iceberg tables + schemas from the catalog_columns mirror.

Reads only from Postgres (the mirror refreshed from Spark Connect every ~30s);
never hits Spark Connect live per request.
"""

from app.config import render_table_consume_snippet
from app.models.catalog_mirror import CatalogColumn
from app.repositories.catalog_mirror_repo import CatalogMirrorRepository
from app.schemas.table import TableColumn, TableSchema


def group_columns(rows: list[CatalogColumn]) -> dict[tuple[str, str], list[TableColumn]]:
    """Group mirror rows into {(namespace, table_name): [TableColumn ordered]}."""
    grouped: dict[tuple[str, str], list[TableColumn]] = {}
    for r in rows:
        grouped.setdefault((r.namespace, r.table_name), []).append(
            TableColumn(name=r.column_name, data_type=r.data_type, ordinal_position=r.ordinal_position)
        )
    for cols in grouped.values():
        cols.sort(key=lambda c: c.ordinal_position)
    return grouped


def build_table_schema(namespace: str, table_name: str, columns: list[TableColumn]) -> TableSchema:
    return TableSchema(
        namespace=namespace,
        table_name=table_name,
        columns=columns,
        consume_snippet=render_table_consume_snippet(namespace, table_name),
    )


class TableService:
    def __init__(self, mirror_repo: CatalogMirrorRepository):
        self.mirror_repo = mirror_repo

    async def list_tables(self, team: str | None = None, q: str | None = None) -> list[TableSchema]:
        """All catalog tables (one per namespace+table), filterable by team and name."""
        rows = await self.mirror_repo.list_all()
        grouped = group_columns(rows)
        ns_filter = team.lower() if team else None
        q_lower = q.lower() if q else None

        items: list[TableSchema] = []
        for (namespace, table_name), columns in grouped.items():
            if ns_filter and namespace.lower() != ns_filter:
                continue
            if q_lower and q_lower not in table_name.lower():
                continue
            items.append(build_table_schema(namespace, table_name, columns))

        items.sort(key=lambda t: (t.namespace, t.table_name))
        return items
