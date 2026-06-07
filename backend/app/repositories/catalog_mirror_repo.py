"""Repository for the catalog mirror (catalog_columns) table."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog_mirror import CatalogColumn


class CatalogMirrorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[CatalogColumn]:
        """Return every mirrored column, ordered by table then ordinal position."""
        stmt = select(CatalogColumn).order_by(
            CatalogColumn.table_name, CatalogColumn.ordinal_position
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def replace_all(self, rows: list[dict]) -> int:
        """Replace the entire mirror in one transaction (delete-all then bulk insert).

        Atomic per commit: concurrent readers see either the old snapshot or the
        new one, never an empty table. Caller is responsible for ``commit()``.
        Returns the number of rows inserted.
        """
        await self.session.execute(delete(CatalogColumn))
        await self.session.flush()
        self.session.add_all([CatalogColumn(**row) for row in rows])
        return len(rows)
