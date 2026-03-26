"""User management endpoints — admin listing, role updates, and activation."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_role
from app.dependencies import get_user_repo
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    ActiveUpdateRequest,
    RoleUpdateRequest,
    UserListResponse,
    user_to_response,
)
from app.services.user_auth_service import invalidate_user_cache

audit_logger = logging.getLogger("audit")
router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    user: User = Depends(require_role("admin")),
    repo: UserRepository = Depends(get_user_repo),
) -> UserListResponse:
    """List all users with team memberships (admin only)."""
    users = await repo.get_all(skip=skip, limit=limit)
    total = await repo.count_all()
    return UserListResponse(
        items=[user_to_response(u) for u in users],
        total=total,
    )


@router.patch("/{user_id}/role")
async def update_user_role(
    user_id: uuid.UUID,
    body: RoleUpdateRequest,
    user: User = Depends(require_role("admin")),
    repo: UserRepository = Depends(get_user_repo),
) -> dict:
    """Change a user's global role (admin only)."""
    # SEC-08: Block self-demotion
    if user_id == user.id and body.role != user.role:
        raise HTTPException(
            status_code=400,
            detail="Cannot change your own role",
        )

    # SEC-08: Last-admin guard
    if body.role != "admin":
        target_user = await repo.get_by_id(user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        if target_user.role == "admin":
            admin_count = await repo.count_by_role("admin")
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot demote the last admin user",
                )

    updated = await repo.update_role(user_id, body.role)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    audit_logger.info("role_changed", extra={"target_user_id": str(user_id), "new_role": body.role, "changed_by": user.display_name})
    await invalidate_user_cache()
    return {"ok": True}


@router.patch("/{user_id}/active")
async def update_user_active(
    user_id: uuid.UUID,
    body: ActiveUpdateRequest,
    user: User = Depends(require_role("admin")),
    repo: UserRepository = Depends(get_user_repo),
) -> dict:
    """Activate or deactivate a user account (admin only)."""
    if user_id == user.id and not body.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate yourself",
        )

    updated = await repo.update_active(user_id, body.is_active)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    await invalidate_user_cache()
    return {"ok": True}
