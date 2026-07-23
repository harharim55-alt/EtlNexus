"""Data product endpoints — list, detail, create, edit, delete + revisions."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.auth import (
    AuthUser,
    get_current_user,
    require_product_visibility,
    require_team_membership,
)
from app.config import settings
from app.dependencies import get_data_product_service, get_revision_repo
from app.repositories.revision_repo import RevisionRepository
from app.schemas.common import SuccessResponse
from app.schemas.data_product import (
    DataProductDetail,
    DataProductListResponse,
    DataProductUpdateRequest,
    DataProductUpdateResponse,
    ProductRevisionResponse,
    RevisionListResponse,
)
from app.services.data_product_service import DataProductService, DuplicateProductNameError

router = APIRouter(prefix="/api/data-products", tags=["data-products"])


# ---------- Request bodies ----------


class DataProductCreateRequest(BaseModel):
    name: str
    description: str | None = None
    documentation: str | None = None
    schedule_type: str | None = None
    # Team to register the product under. Required when the creator belongs to more
    # than one team; ignored (auto-filled) when they have exactly one.
    team: str | None = None
    # Full table names, e.g. ["vault.logins", "prism.events"].
    tables: list[str] = []


class DataProductTablesRequest(BaseModel):
    tables: list[str] = []


# ---------- List / detail ----------


@router.get("", response_model=DataProductListResponse)
async def list_data_products(
    q: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(settings.default_page_limit, ge=1, le=500),
    team: list[str] | None = Query(None),
    schedule: list[str] | None = Query(None),
    user: AuthUser = Depends(get_current_user),
    service: DataProductService = Depends(get_data_product_service),
):
    return await service.list_products(
        query=q,
        skip=skip,
        limit=limit,
        team_names=team,
        schedule_types=schedule,
    )


@router.get("/{product_id}", response_model=DataProductDetail)
async def get_data_product(
    product_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
    service: DataProductService = Depends(get_data_product_service),
):
    result = await service.get_product_detail_for_user(
        product_id=product_id,
        user_teams=set(user.teams),
        user_role=user.role,
        is_master=user.is_master,
        username=user.username,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Data product not found")
    return result


# ---------- Create / edit / delete ----------


@router.post("", response_model=DataProductDetail, status_code=201)
async def create_data_product(
    body: DataProductCreateRequest,
    user: AuthUser = Depends(get_current_user),
    service: DataProductService = Depends(get_data_product_service),
):
    """Create a data product owned by the creator's team from selected catalog tables."""
    is_privileged = user.role == "admin" or user.is_master
    if not is_privileged and user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot create data products")

    # Resolve the owning team. A chosen team must be one the user belongs to (master
    # admins may register under any team). With no choice: use the single team, require
    # a choice when there are several, or None when the user has no teams.
    chosen = (body.team or "").strip() or None
    if chosen:
        if not user.is_master and chosen.lower() not in {t.lower() for t in user.teams}:
            raise HTTPException(status_code=403, detail="You can only create a product under a team you belong to")
        team = chosen
    elif len(user.teams) == 1:
        team = user.teams[0]
    elif len(user.teams) > 1:
        raise HTTPException(
            status_code=400,
            detail="You belong to multiple teams — choose which team to register the product under",
        )
    else:  # no teams — allowed; the product simply has no owning team, and only
        team = None  # its creator can edit it (enforced by require_team_membership).

    try:
        return await service.create_product(
            name=body.name,
            description=body.description,
            documentation=body.documentation,
            team=team,
            schedule_type=body.schedule_type,
            created_by=user.username,
            tables=body.tables,
        )
    except DuplicateProductNameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch(
    "/{product_id}",
    response_model=DataProductUpdateResponse,
    dependencies=[Depends(require_team_membership("product_id"))],
)
async def update_data_product(
    request: Request,
    product_id: uuid.UUID,
    body: DataProductUpdateRequest,
    user: AuthUser = Depends(get_current_user),
    service: DataProductService = Depends(get_data_product_service),
    revision_repo: RevisionRepository = Depends(get_revision_repo),
):
    preloaded = getattr(request.state, "product", None)
    try:
        result = await service.update_product_metadata(
            product_id,
            body,
            updated_by=user.username,
            preloaded_product=preloaded,
            revision_repo=revision_repo,
        )
    except DuplicateProductNameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=404, detail="Data product not found")
    return result


@router.put(
    "/{product_id}/tables",
    response_model=DataProductDetail,
    dependencies=[Depends(require_team_membership("product_id"))],
)
async def set_data_product_tables(
    product_id: uuid.UUID,
    body: DataProductTablesRequest,
    user: AuthUser = Depends(get_current_user),
    service: DataProductService = Depends(get_data_product_service),
):
    """Replace the set of tables a data product references (any team's tables)."""
    result = await service.set_product_tables(product_id, body.tables, updated_by=user.username)
    if not result:
        raise HTTPException(status_code=404, detail="Data product not found")
    return result


@router.delete(
    "/{product_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(require_team_membership("product_id"))],
)
async def delete_data_product(
    product_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
    service: DataProductService = Depends(get_data_product_service),
):
    """Delete a data product (owning-team members / master only)."""
    deleted = await service.delete_product(product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Data product not found")
    return SuccessResponse()


# ---------- Revisions ----------


@router.get(
    "/{product_id}/revisions",
    response_model=RevisionListResponse,
    dependencies=[Depends(require_product_visibility("product_id"))],
)
async def list_revisions(
    product_id: uuid.UUID,
    field: str | None = Query(None, pattern="^(description|documentation)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: AuthUser = Depends(get_current_user),
    revision_repo: RevisionRepository = Depends(get_revision_repo),
):
    items, total = await revision_repo.list_by_product(product_id, field_name=field, skip=skip, limit=limit)
    return RevisionListResponse(
        items=[ProductRevisionResponse.model_validate(r) for r in items],
        total=total,
    )


@router.post(
    "/{product_id}/revisions/{revision_id}/restore",
    response_model=DataProductUpdateResponse,
    dependencies=[Depends(require_team_membership("product_id"))],
)
async def restore_revision(
    product_id: uuid.UUID,
    revision_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
    service: DataProductService = Depends(get_data_product_service),
    revision_repo: RevisionRepository = Depends(get_revision_repo),
):
    result = await service.restore_revision(
        product_id,
        revision_id,
        restored_by=user.username,
        revision_repo=revision_repo,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Data product or revision not found")
    return result
