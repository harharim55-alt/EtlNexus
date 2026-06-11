"""Tag repository — tags are data products (Pipeline with is_tag); the
product_tags table links a product to its tag-products."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline import Pipeline
from app.models.product_tag import ProductTag


class TagRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_tags(self) -> list[Pipeline]:
        """All tag-products, ordered by name."""
        stmt = select(Pipeline).where(Pipeline.is_tag.is_(True)).order_by(Pipeline.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def tags_for_product(self, product_id: uuid.UUID) -> list[Pipeline]:
        """Tag-products applied to the given product."""
        stmt = (
            select(Pipeline)
            .join(ProductTag, ProductTag.tag_id == Pipeline.id)
            .where(ProductTag.product_id == product_id)
            .order_by(Pipeline.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def members_of_tag(self, tag_id: uuid.UUID) -> list[Pipeline]:
        """Products tagged with the given tag-product."""
        stmt = (
            select(Pipeline)
            .join(ProductTag, ProductTag.product_id == Pipeline.id)
            .where(ProductTag.tag_id == tag_id)
            .order_by(Pipeline.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_product_tags(self, product_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> None:
        """Replace the set of tags applied to a product."""
        await self.session.execute(
            delete(ProductTag).where(ProductTag.product_id == product_id)
        )
        for tid in dict.fromkeys(tag_ids):  # dedupe, preserve order
            self.session.add(ProductTag(product_id=product_id, tag_id=tid))
        await self.session.flush()
