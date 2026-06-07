"""Catalog mirror model — a Postgres copy of the Iceberg table schemas.

A background job reads the catalog from Spark Connect every
``CATALOG_MIRROR_INTERVAL_SECONDS`` and replaces the rows in this table, so
end-user requests read schema data from Postgres and never hit Spark Connect
live. One row per column of a table; grain matches ``SparkTableSchema.fields``.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CatalogColumn(Base):
    __tablename__ = "catalog_columns"
    __table_args__ = (
        UniqueConstraint("namespace", "table_name", "column_name", name="uq_catalog_col"),
        Index("ix_catalog_columns_ns_table", "namespace", "table_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    namespace: Mapped[str] = mapped_column(String(255), index=True)
    table_name: Mapped[str] = mapped_column(String(255), index=True)
    column_name: Mapped[str] = mapped_column(String(255), index=True)
    data_type: Mapped[str | None] = mapped_column(String(50))
    ordinal_position: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
