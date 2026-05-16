"""Network endpoints — admin-managed list of available networks."""

import uuid

from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_role
from app.dependencies import get_network_service
from app.models.user import User
from app.schemas.network import (
    NetworkCreateRequest,
    NetworkListResponse,
    NetworkResponse,
    NetworkUpdateRequest,
)
from app.services.network_service import NetworkService

router = APIRouter(prefix="/api/networks", tags=["networks"])


@router.get("", response_model=NetworkListResponse)
async def list_networks(
    user: User = Depends(get_current_user),
    service: NetworkService = Depends(get_network_service),
):
    networks = await service.list_networks()
    return NetworkListResponse(items=[NetworkResponse.model_validate(n) for n in networks])


@router.post("", response_model=NetworkResponse, status_code=201)
async def create_network(
    body: NetworkCreateRequest,
    user: User = Depends(require_role("admin")),
    service: NetworkService = Depends(get_network_service),
):
    network = await service.create_network(name=body.name, description=body.description)
    return NetworkResponse.model_validate(network)


@router.patch("/{network_id}", response_model=NetworkResponse)
async def update_network(
    network_id: uuid.UUID,
    body: NetworkUpdateRequest,
    user: User = Depends(require_role("admin")),
    service: NetworkService = Depends(get_network_service),
):
    network = await service.update_network(network_id, **body.model_dump(exclude_unset=True))
    return NetworkResponse.model_validate(network)


@router.delete("/{network_id}", status_code=204)
async def delete_network(
    network_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    service: NetworkService = Depends(get_network_service),
):
    await service.delete_network(network_id)
