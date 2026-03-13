"""Bouncer endpoints — list bouncers and query downstream topology."""

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.dependencies import get_bouncer_service
from app.models.user import User
from app.schemas.sensor import BouncerListResponse, BouncerTopologyResponse
from app.services.sensor_service import BouncerService

router = APIRouter(prefix="/api/bouncers", tags=["bouncers"])


@router.get("", response_model=BouncerListResponse)
async def list_bouncers(
    team: str | None = Query(None, description="Filter by team name"),
    user: User = Depends(get_current_user),
    service: BouncerService = Depends(get_bouncer_service),
):
    return await service.get_all_bouncers(team=team)


@router.get("/topology", response_model=BouncerTopologyResponse)
async def get_bouncer_topology(
    bouncers: list[str] = Query(..., description="Bouncer names to query"),
    mode: str = Query("union", description="union or intersection"),
    user: User = Depends(get_current_user),
    service: BouncerService = Depends(get_bouncer_service),
):
    return await service.get_bouncer_topology(bouncer_names=bouncers, mode=mode)
