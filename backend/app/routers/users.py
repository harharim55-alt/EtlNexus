"""User management endpoints — admin read-only user directory.

Identity, roles and (de)activation are owned by Keycloak; the app only mirrors
them. Team membership is managed via the teams endpoints. So this router only
exposes a read-only listing.
"""

from fastapi import APIRouter, Depends, Query

from app.auth import require_role
from app.dependencies import get_user_repo
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import UserListResponse, user_to_response

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    user: User = Depends(require_role("admin")),
    repo: UserRepository = Depends(get_user_repo),
) -> UserListResponse:
    """List all users with team memberships (admin only, read-only)."""
    users = await repo.get_all(skip=skip, limit=limit)
    total = await repo.count_all()
    return UserListResponse(
        items=[user_to_response(u) for u in users],
        total=total,
    )
