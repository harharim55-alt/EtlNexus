"""Tag service — tags are data products (Pipeline with is_tag)."""

import uuid

from app.repositories.tag_repo import TagRepository


class TagService:
    def __init__(self, tag_repo: TagRepository):
        self.tag_repo = tag_repo

    async def list_tags(self):
        """All tag-products."""
        return await self.tag_repo.list_tags()

    async def tags_for_product(self, product_id: uuid.UUID):
        return await self.tag_repo.tags_for_product(product_id)

    async def members_of_tag(self, tag_id: uuid.UUID):
        return await self.tag_repo.members_of_tag(tag_id)

    async def set_product_tags(self, product_id: uuid.UUID, tag_ids: list[uuid.UUID]):
        await self.tag_repo.set_product_tags(product_id, tag_ids)
        await self.tag_repo.session.commit()
        return await self.tag_repo.tags_for_product(product_id)
