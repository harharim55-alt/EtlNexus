"""Sensor endpoints — list sensors and query downstream topology."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.dependencies import get_sensor_service
from app.models.user import User
from app.schemas.sensor import SensorListResponse, SensorTopologyResponse
from app.services.sensor_service import SensorService

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.get("", response_model=SensorListResponse)
async def list_sensors(
    team: Optional[str] = Query(None, description="Filter by team name"),
    user: User = Depends(get_current_user),
    service: SensorService = Depends(get_sensor_service),
):
    return await service.get_all_sensors(team=team)


@router.get("/topology", response_model=SensorTopologyResponse)
async def get_sensor_topology(
    sensors: list[str] = Query(..., description="Sensor names to query"),
    mode: str = Query("union", description="union or intersection"),
    user: User = Depends(get_current_user),
    service: SensorService = Depends(get_sensor_service),
):
    return await service.get_sensor_topology(sensor_names=sensors, mode=mode)
