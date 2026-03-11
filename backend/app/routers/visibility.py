"""Visibility grant endpoints — admin management of cross-team pipeline access."""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_role
from app.dependencies import get_visibility_service
from app.models.user import User
from app.models.visibility_grant import VisibilityGrant
from app.schemas.visibility import VisibilityGrantRequest, VisibilityGrantResponse
from app.services.visibility_service import VisibilityService

router = APIRouter(prefix="/api/visibility", tags=["visibility"])


def _grant_to_response(g: VisibilityGrant) -> VisibilityGrantResponse:
    """Convert a VisibilityGrant ORM instance to a response schema."""
    return VisibilityGrantResponse(
        id=str(g.id),
        grantee_team_id=str(g.grantee_team_id) if g.grantee_team_id else None,
        grantee_team_name=g.grantee_team.name if g.grantee_team else None,
        grantee_user_id=str(g.grantee_user_id) if g.grantee_user_id else None,
        grantee_user_name=g.grantee_user.display_name if g.grantee_user else None,
        grantee_user_email=g.grantee_user.email if g.grantee_user else None,
        pipeline_id=str(g.pipeline_id) if g.pipeline_id else None,
        source_team_id=str(g.source_team_id) if g.source_team_id else None,
        source_team_name=None,
        grant_level=g.grant_level,
        granted_by=g.granted_by,
        created_at=g.created_at.isoformat(),
    )


@router.get("/grants", response_model=list[VisibilityGrantResponse])
async def list_grants(
    user: User = Depends(require_role("admin")),
    service: VisibilityService = Depends(get_visibility_service),
) -> list[VisibilityGrantResponse]:
    """List all visibility grants (admin only)."""
    grants = await service.list_grants()
    return [_grant_to_response(g) for g in grants]


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
    if not body.pipeline_id and not body.source_team_id:
        raise HTTPException(
            status_code=400,
            detail="Must specify pipeline_id or source_team_id",
        )
    if body.pipeline_id and body.source_team_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot specify both pipeline_id and source_team_id",
        )
    if not body.grantee_team_id and not body.grantee_user_id:
        raise HTTPException(
            status_code=400,
            detail="Must specify grantee_team_id or grantee_user_id",
        )
    if body.grantee_team_id and body.grantee_user_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot specify both grantee_team_id and grantee_user_id",
        )

    try:
        grantee_team_uuid = uuid.UUID(body.grantee_team_id) if body.grantee_team_id else None
        grantee_user_uuid = uuid.UUID(body.grantee_user_id) if body.grantee_user_id else None
        pipeline_uuid = uuid.UUID(body.pipeline_id) if body.pipeline_id else None
        source_team_uuid = (
            uuid.UUID(body.source_team_id) if body.source_team_id else None
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid UUID: {exc}") from exc

    if body.grant_level not in ("viewer", "editor"):
        raise HTTPException(
            status_code=400,
            detail="grant_level must be 'viewer' or 'editor'",
        )

    grant = await service.create_grant(
        pipeline_id=pipeline_uuid,
        source_team_id=source_team_uuid,
        grantee_team_id=grantee_team_uuid,
        grantee_user_id=grantee_user_uuid,
        granted_by=user.display_name,
        grant_level=body.grant_level,
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
