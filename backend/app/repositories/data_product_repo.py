"""Repository for data products (``ui_catalog_data_products``)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_product import DataProduct

_UNSET = object()


def _escape_like(value: str) -> str:
    """Escape LIKE special characters so they are treated as literals."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class DataProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, product_id: uuid.UUID) -> DataProduct | None:
        result = await self.session.execute(select(DataProduct).where(DataProduct.id == product_id))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[DataProduct]:
        """All products, ordered by name (used to build AI catalog context)."""
        result = await self.session.execute(select(DataProduct).order_by(DataProduct.name))
        return list(result.scalars().all())

    async def list_products(
        self,
        *,
        query: str | None = None,
        team_names: list[str] | None = None,
        schedule_types: list[str] | None = None,
        skip: int = 0,
        limit: int = 200,
    ) -> tuple[list[DataProduct], int]:
        """Return (products, total) filtered by optional text search / team / schedule.

        Every authenticated user may view every product; edit is gated separately
        by team membership, so there is no view-time team scoping here.
        """
        conditions = []

        if query:
            pattern = f"%{_escape_like(query)}%"
            conditions.append(
                or_(
                    DataProduct.name.ilike(pattern, escape="\\"),
                    DataProduct.description.ilike(pattern, escape="\\"),
                    # Match a referenced table name within the text[] array.
                    func.array_to_string(DataProduct.tables, ",").ilike(pattern, escape="\\"),
                )
            )
        if team_names:
            conditions.append(DataProduct.team.in_(team_names))
        if schedule_types:
            conditions.append(DataProduct.schedule_type.in_(schedule_types))

        count_stmt = select(func.count()).select_from(DataProduct)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar_one()

        data_stmt = select(DataProduct).order_by(DataProduct.name).offset(skip).limit(limit)
        if conditions:
            data_stmt = data_stmt.where(*conditions)
        result = await self.session.execute(data_stmt)
        return list(result.scalars().all()), total

    async def create(
        self,
        *,
        name: str,
        description: str | None,
        documentation: str | None,
        team: str | None,
        schedule_type: str | None,
        created_by: str,
        tables: list[str],
    ) -> DataProduct:
        """Insert a new data product and flush (caller commits)."""
        product = DataProduct(
            name=name,
            description=description,
            documentation=documentation,
            team=team,
            schedule_type=schedule_type,
            tables=_dedupe(tables),
            created_by=created_by,
            last_updated_by=created_by,
            last_updated_at=datetime.now(UTC),
        )
        self.session.add(product)
        await self.session.flush()
        return product

    async def update_metadata(
        self,
        product_id: uuid.UUID,
        *,
        name=_UNSET,
        description=_UNSET,
        documentation=_UNSET,
        schedule_type=_UNSET,
        updated_by: str = "System",
        product: DataProduct | None = None,
    ) -> DataProduct | None:
        if product is None:
            product = await self.get_by_id(product_id)
        if not product:
            return None
        if name is not _UNSET and name:
            product.name = name
        if description is not _UNSET:
            product.description = description
        if documentation is not _UNSET:
            product.documentation = documentation
        if schedule_type is not _UNSET:
            product.schedule_type = schedule_type
        product.last_updated_by = updated_by
        product.last_updated_at = datetime.now(UTC)
        await self.session.flush()
        return product

    async def set_tables(self, product_id: uuid.UUID, tables: list[str]) -> DataProduct | None:
        """Replace the product's referenced tables (deduped)."""
        product = await self.get_by_id(product_id)
        if not product:
            return None
        product.tables = _dedupe(tables)
        await self.session.flush()
        return product

    async def delete(self, product_id: uuid.UUID) -> bool:
        """Delete a product; its revisions cascade via the FK (ON DELETE CASCADE)."""
        result = await self.session.execute(delete(DataProduct).where(DataProduct.id == product_id))
        return result.rowcount > 0


def _dedupe(tables: list[str]) -> list[str]:
    """Deduplicate full table names while preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for t in tables:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out
