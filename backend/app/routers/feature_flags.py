"""Feature flag endpoints — check and manage feature access."""

import uuid

from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_role
from app.dependencies import get_feature_flag_service
from app.models.user import User
from app.schemas.feature_flag import (
    FeatureFlagCheckResponse,
    FeatureFlagListResponse,
    FeatureFlagResponse,
    FeatureFlagUpdateRequest,
)
from app.services.feature_flag_service import FeatureFlagService

router = APIRouter(prefix="/api/feature-flags", tags=["feature-flags"])


@router.get("", response_model=FeatureFlagListResponse)
async def list_feature_flags(
    user: User = Depends(get_current_user),
    service: FeatureFlagService = Depends(get_feature_flag_service),
):
    flags = await service.list_flags()
    return FeatureFlagListResponse(
        items=[FeatureFlagResponse.model_validate(f) for f in flags]
    )


@router.get("/check/{flag_name}", response_model=FeatureFlagCheckResponse)
async def check_feature_flag(
    flag_name: str,
    user: User = Depends(get_current_user),
    service: FeatureFlagService = Depends(get_feature_flag_service),
):
    accessible = await service.check_access(flag_name, is_beta=user.is_beta)
    return FeatureFlagCheckResponse(name=flag_name, accessible=accessible)


@router.put("/{flag_id}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    flag_id: uuid.UUID,
    body: FeatureFlagUpdateRequest,
    user: User = Depends(require_role("admin")),
    service: FeatureFlagService = Depends(get_feature_flag_service),
):
    flag = await service.update_flag(flag_id, **body.model_dump(exclude_unset=True))
    return FeatureFlagResponse.model_validate(flag)
