"""Tables endpoint — lists Iceberg catalog tables + schemas from the mirror."""

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.dependencies import get_table_service
from app.models.user import User
from app.schemas.table import TableListResponse
from app.services.table_service import TableService

router = APIRouter(prefix="/api/tables", tags=["tables"])


@router.get("", response_model=TableListResponse)
async def list_tables(
    team: str | None = Query(None, description="Filter to a single team's namespace"),
    q: str | None = Query(None, description="Filter by table name substring"),
    user: User = Depends(get_current_user),
    service: TableService = Depends(get_table_service),
) -> TableListResponse:
    """All catalog tables (namespace + schema + per-table consume snippet)."""
    items = await service.list_tables(team=team, q=q)
    return TableListResponse(items=items, total=len(items))
