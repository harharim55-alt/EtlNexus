"""Pydantic schemas for catalog tables (read from the catalog_columns mirror)."""

from pydantic import BaseModel


class TableColumn(BaseModel):
    name: str
    data_type: str | None = None
    ordinal_position: int = 0


class TableSchema(BaseModel):
    namespace: str
    table_name: str
    columns: list[TableColumn] = []
    consume_snippet: str = ""


class TableListResponse(BaseModel):
    items: list[TableSchema]
    total: int
