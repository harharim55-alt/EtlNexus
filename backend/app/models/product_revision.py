"""Product revision model — edit history of a data product's text fields.

Snapshots the previous value of ``description`` / ``documentation`` before each
change so edits can be reviewed and restored.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductRevision(Base):
    __tablename__ = "ui_catalog_product_revisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ui_catalog_data_products.id", ondelete="CASCADE"), index=True
    )
    field_name: Mapped[str] = mapped_column(String(50))
    content: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[str] = mapped_column(String(255))
    change_source: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["DataProduct"] = relationship(back_populates="revisions")


from app.models.data_product import DataProduct
