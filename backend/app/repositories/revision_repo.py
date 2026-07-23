import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_revision import ProductRevision


class RevisionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        product_id: uuid.UUID,
        field_name: str,
        content: str | None,
        changed_by: str,
        change_source: str = "user",
    ) -> ProductRevision:
        """Snapshot the previous value of a field before it changes."""
        revision = ProductRevision(
            product_id=product_id,
            field_name=field_name,
            content=content,
            changed_by=changed_by,
            change_source=change_source,
        )
        self.session.add(revision)
        await self.session.flush()
        return revision

    async def list_by_product(
        self,
        product_id: uuid.UUID,
        field_name: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ProductRevision], int]:
        conditions = [ProductRevision.product_id == product_id]
        if field_name:
            conditions.append(ProductRevision.field_name == field_name)

        count_stmt = select(func.count()).select_from(ProductRevision).where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar_one()

        data_stmt = (
            select(ProductRevision)
            .where(*conditions)
            .order_by(ProductRevision.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(data_stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, revision_id: uuid.UUID) -> ProductRevision | None:
        stmt = select(ProductRevision).where(ProductRevision.id == revision_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
