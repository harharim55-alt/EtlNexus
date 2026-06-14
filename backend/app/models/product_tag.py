"""ProductTag — links a data product to a tag (which is itself a data product).

Both sides reference ``pipelines.id``: ``product_id`` is the tagged product and
``tag_id`` is the tag-product (a Pipeline with ``is_tag=True``).
"""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProductTag(Base):
    __tablename__ = "product_tags"
    __table_args__ = (
        UniqueConstraint("product_id", "tag_id", name="uq_product_tag"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), index=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), index=True
    )
