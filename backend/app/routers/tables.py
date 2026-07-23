"""Tables endpoints — list catalog tables (from the external metrics table) and
read a single table's schema live from Spark Connect on demand."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import AuthUser, get_current_user
from app.dependencies import get_table_service
from app.schemas.table import NamespaceListResponse, TableListResponse, TableSchema
from app.services.table_service import TableService

router = APIRouter(prefix="/api/tables", tags=["tables"])


@router.get("", response_model=TableListResponse)
async def list_tables(
    team: list[str] | None = Query(None, description="Filter to one or more team namespaces"),
    q: str | None = Query(None, description="Filter by table name substring"),
    user: AuthUser = Depends(get_current_user),
    service: TableService = Depends(get_table_service),
) -> TableListResponse:
    """All catalog tables (namespace + name). Schema is fetched separately."""
    items = await service.list_tables(team_names=team, q=q)
    return TableListResponse(items=items, total=len(items))


@router.get("/namespaces", response_model=NamespaceListResponse)
async def list_namespaces(
    user: AuthUser = Depends(get_current_user),
    service: TableService = Depends(get_table_service),
) -> NamespaceListResponse:
    """Distinct namespaces present in the catalog (for the team filter)."""
    return NamespaceListResponse(items=await service.list_namespaces())


@router.get("/schema", response_model=TableSchema)
async def get_table_schema(
    namespace: str = Query(..., description="Table namespace (db_name)"),
    table: str = Query(..., description="Table name (tbl_name)"),
    user: AuthUser = Depends(get_current_user),
    service: TableService = Depends(get_table_service),
) -> TableSchema:
    """Read a single table's schema live from Spark Connect."""
    result = await service.get_table_schema(namespace, table)
    if result is None:
        raise HTTPException(status_code=404, detail="Table schema not available")
    return result
