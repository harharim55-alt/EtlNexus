"""Visibility grant endpoints — admin management of cross-team pipeline access."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_role
from app.dependencies import get_visibility_service
from app.models.user import User
from app.models.visibility_grant import VisibilityGrant
from app.schemas.visibility import GrantListResponse, VisibilityGrantRequest, VisibilityGrantResponse
from app.services.visibility_service import VisibilityService

router = APIRouter(prefix="/api/visibility", tags=["visibility"])


def _grant_to_response(g: VisibilityGrant) -> VisibilityGrantResponse:
    """Convert a VisibilityGrant ORM instance to a response schema."""
    return VisibilityGrantResponse(
        id=g.id,
        grantee_team_id=g.grantee_team_id,
        grantee_team_name=g.grantee_team.name if g.grantee_team else None,
        grantee_user_id=g.grantee_user_id,
        grantee_user_name=g.grantee_user.display_name if g.grantee_user else None,
        grantee_user_email=g.grantee_user.email if g.grantee_user else None,
        pipeline_id=g.pipeline_id,
        source_team_id=g.source_team_id,
        source_team_name=g.source_team.name if g.source_team else None,
        grant_level=g.grant_level,
        granted_by=g.granted_by,
        granted_by_user_id=g.granted_by_user_id,
        created_at=g.created_at,
    )


@router.get("/grants", response_model=GrantListResponse)
async def list_grants(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    user: User = Depends(require_role("admin")),
    service: VisibilityService = Depends(get_visibility_service),
) -> GrantListResponse:
    """List all visibility grants (admin only)."""
    grants, total = await service.list_grants(skip=skip, limit=limit)
    return GrantListResponse(
        items=[_grant_to_response(g) for g in grants],
        total=total,
    )


@router.post("/grants", response_model=VisibilityGrantResponse, status_code=201)
async def create_grant(
    body: VisibilityGrantRequest,
    user: User = Depends(require_role("admin")),
    service: VisibilityService = Depends(get_visibility_service),
) -> VisibilityGrantResponse:
    """Create a visibility grant (admin only).

    Exactly one of ``pipeline_id`` or ``source_team_id`` must be set (target).
    Exactly one of ``grantee_team_id`` or ``grantee_user_id`` must be set (recipient).
    """
    grant = await service.create_grant(
        pipeline_id=body.pipeline_id,
        source_team_id=body.source_team_id,
        grantee_team_id=body.grantee_team_id,
        grantee_user_id=body.grantee_user_id,
        granted_by=user.display_name,
        grant_level=body.grant_level,
        granted_by_user_id=user.id,
    )

    return _grant_to_response(grant)


@router.delete("/grants/{grant_id}")
async def delete_grant(
    grant_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    service: VisibilityService = Depends(get_visibility_service),
) -> dict:
    """Revoke a visibility grant (admin only)."""
    deleted = await service.delete_grant(grant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Grant not found")
    return {"ok": True}
