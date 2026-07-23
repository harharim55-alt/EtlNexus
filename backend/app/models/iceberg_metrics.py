"""External Iceberg metrics table (read-only).

``iceberg_table_metrics`` is provided by an outside system and already exists in
the database we connect to. The app NEVER creates or writes it — it only reads
two columns to learn which Iceberg tables exist:

  - ``db_name``  — the namespace under the Spark catalog
  - ``tbl_name`` — the table name

It is declared as a Core ``Table`` on its own ``MetaData`` (deliberately NOT
``Base.metadata``) so that ``Base.metadata.create_all`` can never emit DDL for
it. The table name is configurable via ``ICEBERG_METRICS_TABLE``.
"""

from sqlalchemy import Column, Date, MetaData, Table, Text

from app.config import settings

# Standalone metadata — intentionally separate from Base.metadata so the
# create-tables-on-startup step never touches this externally-owned table.
external_metadata = MetaData()

# Schema to read the external table from. Explicit ICEBERG_METRICS_SCHEMA wins;
# otherwise default to the app schema (DB_SCHEMA), or None (public) when DB_SCHEMA is
# public. We qualify it explicitly rather than relying on search_path so it works
# through connection poolers (PgBouncer rejects a search_path startup parameter).
_metrics_schema = settings.iceberg_metrics_schema or (
    settings.db_schema if settings.db_schema != "public" else None
)

iceberg_table_metrics = Table(
    settings.iceberg_metrics_table,
    external_metadata,
    Column("db_name", Text),
    Column("tbl_name", Text),
    # Snapshot date (YYYY-MM-DD). Listings are filtered to a single date (see repo).
    Column("date", Date),
    schema=_metrics_schema,
)
