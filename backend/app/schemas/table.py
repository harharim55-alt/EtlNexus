"""Pydantic schemas for catalog tables.

Table existence comes from the external ``iceberg_table_metrics`` table; a
single table's columns are read live from Spark Connect on demand.
"""

from pydantic import BaseModel


class TableColumn(BaseModel):
    name: str
    data_type: str | None = None
    ordinal_position: int = 0


class TableRef(BaseModel):
    """A reference to a catalog table (no schema)."""

    namespace: str
    table_name: str


class TableListItem(BaseModel):
    namespace: str
    table_name: str


class TableListResponse(BaseModel):
    items: list[TableListItem]
    total: int


class TableSchema(BaseModel):
    """A table's live schema (columns) + its consume snippet."""

    namespace: str
    table_name: str
    columns: list[TableColumn] = []
    consume_snippet: str = ""


class NamespaceListResponse(BaseModel):
    items: list[str]
