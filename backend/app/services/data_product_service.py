"""Data product service — CRUD + revision history for data products."""

import uuid

from sqlalchemy.exc import IntegrityError

from app.cache import product_list_cache
from app.config import render_product_consume_snippet
from app.models.data_product import DataProduct
from app.repositories.data_product_repo import DataProductRepository
from app.repositories.revision_repo import RevisionRepository
from app.schemas.data_product import (
    DataProductDetail,
    DataProductListItem,
    DataProductListResponse,
    DataProductUpdateRequest,
    DataProductUpdateResponse,
)
from app.schemas.table import TableRef

RESTORABLE_FIELDS = frozenset({"description", "documentation"})


class DuplicateProductNameError(Exception):
    """Raised when a data product name collides with an existing one."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"A data product named '{name}' already exists.")


def parse_fqn(fqn: str) -> TableRef:
    """Split a full table name ``"namespace.table"`` into a TableRef.

    Splits on the last dot so multi-level namespaces survive; a name with no dot
    is treated as a table with an empty namespace.
    """
    namespace, _, table_name = fqn.rpartition(".")
    if not table_name:  # no dot present
        namespace, table_name = "", fqn
    return TableRef(namespace=namespace, table_name=table_name)


class DataProductService:
    def __init__(
        self,
        repo: DataProductRepository,
        revision_repo: RevisionRepository | None = None,
    ):
        self.repo = repo
        self.revision_repo = revision_repo

    # ---- listing -----------------------------------------------------------

    async def list_products(
        self,
        query: str | None = None,
        skip: int = 0,
        limit: int = 200,
        team_names: list[str] | None = None,
        schedule_types: list[str] | None = None,
    ) -> DataProductListResponse:
        cache_key: str | None = None
        if not (query or team_names or schedule_types):
            cache_key = f"all:{skip}:{limit}"
            cached = product_list_cache.get(cache_key)
            if cached is not None:
                return cached

        products, total = await self.repo.list_products(
            query=query,
            team_names=team_names,
            schedule_types=schedule_types,
            skip=skip,
            limit=limit,
        )
        result = DataProductListResponse(
            items=[
                DataProductListItem(
                    id=p.id,
                    name=p.name,
                    description=p.description,
                    schedule_type=p.schedule_type,
                    team=p.team,
                )
                for p in products
            ],
            total=total,
        )
        if cache_key:
            product_list_cache.set(cache_key, result)
        return result

    # ---- detail ------------------------------------------------------------

    def _to_detail(self, product: DataProduct) -> DataProductDetail:
        return DataProductDetail(
            id=product.id,
            name=product.name,
            description=product.description,
            tables=[parse_fqn(t) for t in (product.tables or [])],
            documentation=product.documentation,
            created_by=product.created_by,
            last_updated_by=product.last_updated_by,
            last_updated_at=product.last_updated_at,
            created_at=product.created_at,
            updated_at=product.updated_at,
            team=product.team,
            default_import_snippet=render_product_consume_snippet(product.name),
            schedule_type=product.schedule_type,
        )

    async def get_product_detail(self, product_id: uuid.UUID) -> DataProductDetail | None:
        product = await self.repo.get_by_id(product_id)
        if not product:
            return None
        return self._to_detail(product)

    async def get_product_detail_for_user(
        self,
        product_id: uuid.UUID,
        user_teams: set[str],
        user_role: str,
        is_master: bool = False,
        username: str | None = None,
    ) -> DataProductDetail | None:
        """Detail with ``can_edit`` set. Every user may view; edit is gated by team
        (or, for unassigned products, by being the creator)."""
        detail = await self.get_product_detail(product_id)
        if not detail:
            return None
        detail.can_edit = _can_edit(
            detail.team, user_teams, user_role, is_master, detail.created_by, username
        )
        return detail

    # ---- mutations ---------------------------------------------------------

    async def create_product(
        self,
        name: str,
        description: str | None,
        documentation: str | None,
        team: str | None,
        schedule_type: str | None,
        created_by: str,
        tables: list[str],
    ) -> DataProductDetail:
        """Create a data product = name + metadata + a list of full table names."""
        try:
            product = await self.repo.create(
                name=name,
                description=description,
                documentation=documentation,
                team=team,
                schedule_type=schedule_type,
                created_by=created_by,
                tables=tables,
            )
            await self.repo.session.commit()
        except IntegrityError as exc:
            await self.repo.session.rollback()
            raise DuplicateProductNameError(name) from exc
        product_list_cache.clear()
        return self._to_detail(product)

    async def update_product_metadata(
        self,
        product_id: uuid.UUID,
        update: DataProductUpdateRequest,
        updated_by: str = "System",
        preloaded_product: DataProduct | None = None,
        revision_repo: RevisionRepository | None = None,
    ) -> DataProductUpdateResponse | None:
        product = preloaded_product or await self.repo.get_by_id(product_id)
        if not product:
            return None

        rev_repo = revision_repo or self.revision_repo

        # Snapshot previous values before applying changes.
        if rev_repo:
            for field_name in ("description", "documentation"):
                if field_name in update.model_fields_set and getattr(update, field_name) != getattr(
                    product, field_name
                ):
                    await rev_repo.create(
                        product_id=product_id,
                        field_name=field_name,
                        content=getattr(product, field_name),
                        changed_by=updated_by,
                        change_source="user",
                    )

        repo_kwargs = {
            f: getattr(update, f)
            for f in ("name", "description", "documentation", "schedule_type")
            if f in update.model_fields_set
        }
        product = await self.repo.update_metadata(product_id, **repo_kwargs, updated_by=updated_by, product=product)
        try:
            await self.repo.session.commit()
        except IntegrityError as exc:
            await self.repo.session.rollback()
            raise DuplicateProductNameError(update.name or "") from exc
        product_list_cache.clear()
        return _to_update_response(product)

    async def set_product_tables(
        self,
        product_id: uuid.UUID,
        tables: list[str],
        updated_by: str = "System",
    ) -> DataProductDetail | None:
        """Replace the set of full table names a data product references."""
        product = await self.repo.set_tables(product_id, tables)
        if not product:
            return None
        product.last_updated_by = updated_by
        await self.repo.session.commit()
        product_list_cache.clear()
        return self._to_detail(product)

    async def delete_product(self, product_id: uuid.UUID) -> bool:
        """Delete a data product (its revisions cascade via the FK)."""
        deleted = await self.repo.delete(product_id)
        if deleted:
            await self.repo.session.commit()
            product_list_cache.clear()
        return deleted

    async def restore_revision(
        self,
        product_id: uuid.UUID,
        revision_id: uuid.UUID,
        restored_by: str,
        revision_repo: RevisionRepository | None = None,
    ) -> DataProductUpdateResponse | None:
        rev_repo = revision_repo or self.revision_repo
        if not rev_repo:
            return None

        product = await self.repo.get_by_id(product_id)
        if not product:
            return None

        revision = await rev_repo.get_by_id(revision_id)
        if not revision or revision.product_id != product_id:
            return None
        if revision.field_name not in RESTORABLE_FIELDS:
            return None

        field_name = revision.field_name
        await rev_repo.create(
            product_id=product_id,
            field_name=field_name,
            content=getattr(product, field_name),
            changed_by=restored_by,
            change_source="restore",
        )
        product = await self.repo.update_metadata(
            product_id, **{field_name: revision.content}, updated_by=restored_by, product=product
        )
        await self.repo.session.commit()
        product_list_cache.clear()
        return _to_update_response(product)


def _can_edit(
    team: str | None,
    user_teams: set[str],
    user_role: str,
    is_master: bool,
    created_by: str | None = None,
    username: str | None = None,
) -> bool:
    """Master admins edit anything; otherwise non-viewers may edit their team's
    products. An unassigned (team-less) product is editable only by its creator.
    Team comparison is case-insensitive."""
    if is_master:
        return True
    if user_role == "viewer":
        return False
    if not team:
        # Unassigned product: only the creator may edit.
        return bool(created_by) and created_by == username
    return team.lower() in {t.lower() for t in user_teams}


def _to_update_response(product: DataProduct) -> DataProductUpdateResponse:
    return DataProductUpdateResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        documentation=product.documentation,
        schedule_type=product.schedule_type,
        last_updated_by=product.last_updated_by,
        last_updated_at=product.last_updated_at,
    )
