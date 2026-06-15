"""Link model — the Iceberg tables that make up a data product.

A data product (``Pipeline`` with ``is_data_product=True``) references a set of
catalog tables by ``(namespace, table_name)``. Each table's schema is read from
the ``catalog_columns`` mirror; the data product itself has no schema of its own.
"""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DataProductTable(Base):
    __tablename__ = "data_product_tables"
    __table_args__ = (
        UniqueConstraint("product_id", "namespace", "table_name", name="uq_data_product_table"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), index=True
    )
    namespace: Mapped[str] = mapped_column(String(255), index=True)
    table_name: Mapped[str] = mapped_column(String(255), index=True)
