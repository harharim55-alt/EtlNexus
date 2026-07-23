"""Data product model — the catalog's core entity.

A data product is a named, documented bundle of Iceberg tables (referenced by
their fully-qualified ``db_name.tbl_name``) owned by a Keycloak team. It carries
no schema of its own; each referenced table's schema is read live from Spark
Connect when a user views it.
"""

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DataProduct(Base):
    __tablename__ = "ui_catalog_data_products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    documentation: Mapped[str | None] = mapped_column(Text)
    # Owning team name, sourced from Keycloak (there is no teams table). NULL =
    # unassigned (editable by any non-viewer).
    team: Mapped[str | None] = mapped_column(String(100), index=True)
    # The full table names this product bundles, e.g. ["vault.logins", "prism.events"].
    tables: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    schedule_type: Mapped[str | None] = mapped_column(String(20))
    created_by: Mapped[str | None] = mapped_column(String(255))
    last_updated_by: Mapped[str | None] = mapped_column(String(255))
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    revisions: Mapped[list["ProductRevision"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductRevision.created_at.desc()",
    )


# Imported at module level so the relationship target class is registered.
from app.models.product_revision import ProductRevision
