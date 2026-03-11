"""FastAPI authentication and authorisation dependencies.

Provides three flavours of dependency injection:

- ``get_current_user`` — requires a valid JWT (or returns a default admin
  when SSO is disabled).
- ``get_current_user_optional`` — same as above but returns ``None`` instead
  of raising when credentials are absent.
- ``require_role(*roles)`` — dependency factory that gates a route behind one
  or more global roles.
- ``require_team_membership(pipeline_id_param)`` — dependency factory that
  ensures the caller belongs to the team that owns the pipeline being accessed.
"""

import logging
import uuid

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_session
from app.integrations.oidc_client import oidc_client
from app.models.user import User
from app.models.user_team import UserTeam

logger = logging.getLogger(__name__)

# HTTPBearer with auto_error=False so we can return 401 ourselves and also
# support the optional variant without FastAPI raising first.
security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Core dependency
# ---------------------------------------------------------------------------


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Validate a Bearer JWT and return (or JIT-create) the matching User.

    When ``settings.sso_enabled`` is ``False`` a stable default admin user
    is returned without checking credentials.

    Args:
        request: FastAPI Request (injected automatically).
        credentials: Bearer token from the Authorization header.
        session: Async DB session.

    Returns:
        Authenticated and persisted User model instance.

    Raises:
        HTTPException(401): When SSO is enabled and the token is absent or
            invalid.
    """
    if not settings.sso_enabled:
        return await _get_or_create_default_user(session)

    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        claims = await oidc_client.validate_token(credentials.credentials)
    except Exception as exc:
        logger.debug("JWT validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    return await _upsert_user_from_claims(session, claims)


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db_session),
) -> User | None:
    """Same as ``get_current_user`` but returns ``None`` instead of raising.

    Useful for routes that offer richer responses to authenticated callers
    but must remain accessible to anonymous users.

    Args:
        request: FastAPI Request.
        credentials: Optional Bearer token.
        session: Async DB session.

    Returns:
        Authenticated User, the default admin user (SSO disabled), or
        ``None`` when SSO is enabled and credentials are absent/invalid.
    """
    if not settings.sso_enabled:
        return await _get_or_create_default_user(session)

    if not credentials:
        return None

    try:
        return await get_current_user(request, credentials, session)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Dependency factories
# ---------------------------------------------------------------------------


def require_role(*roles: str):
    """Return a FastAPI dependency that enforces one of the given global roles.

    Usage::

        @router.delete("/pipelines/{id}", dependencies=[Depends(require_role("admin"))])

    Args:
        *roles: Acceptable role strings.

    Returns:
        Async dependency function that raises ``HTTP 403`` on role mismatch.
    """

    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions — required one of: {list(roles)}",
            )
        return user

    return _check


def require_team_membership(pipeline_id_param: str = "pipeline_id"):
    """Return a dependency that checks the caller belongs to the pipeline's team.

    Admins bypass the check.  Pipelines without an assigned team are
    accessible to everyone.

    Args:
        pipeline_id_param: Name of the path parameter that carries the
            pipeline UUID (default ``"pipeline_id"``).

    Returns:
        Async dependency function that raises ``HTTP 403`` when the user is
        not a member of the owning team.
    """

    async def _check(
        request: Request,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> User:
        # Admins can always proceed
        if user.role == "admin":
            return user

        raw_pipeline_id: str | None = request.path_params.get(pipeline_id_param)
        if not raw_pipeline_id:
            return user

        try:
            pipeline_uuid = uuid.UUID(raw_pipeline_id)
        except ValueError:
            return user

        from app.repositories.pipeline_repo import PipelineRepository

        pipeline = await PipelineRepository(session).get_by_id(pipeline_uuid)

        # Unassigned pipeline — everyone may edit
        if not pipeline or not pipeline.team_id:
            return user

        user_team_ids = {ut.team_id for ut in user.team_memberships}
        if pipeline.team_id not in user_team_ids:
            raise HTTPException(
                status_code=403,
                detail="Not a member of this pipeline's team",
            )

        return user

    return _check


def require_team_membership_or_editor_grant(pipeline_id_param: str = "pipeline_id"):
    """Like ``require_team_membership``, but also allows users with an editor-level grant."""

    async def _check(
        request: Request,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> User:
        if user.role == "admin":
            return user

        raw_pipeline_id: str | None = request.path_params.get(pipeline_id_param)
        if not raw_pipeline_id:
            return user

        try:
            pipeline_uuid = uuid.UUID(raw_pipeline_id)
        except ValueError:
            return user

        from app.repositories.pipeline_repo import PipelineRepository

        pipeline = await PipelineRepository(session).get_by_id(pipeline_uuid)

        if not pipeline or not pipeline.team_id:
            return user

        user_team_ids = {ut.team_id for ut in user.team_memberships}

        # Team member — allowed
        if pipeline.team_id in user_team_ids:
            return user

        # Check for editor-level grant
        from app.repositories.visibility_grant_repo import VisibilityGrantRepository

        has_editor = await VisibilityGrantRepository(session).has_editor_grant(
            pipeline_id=pipeline_uuid,
            user_id=user.id,
            user_team_ids=user_team_ids,
        )
        if has_editor:
            return user

        raise HTTPException(
            status_code=403,
            detail="Not a member of this pipeline's team and no editor grant",
        )

    return _check


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _upsert_user_from_claims(
    session: AsyncSession,
    claims: dict,
) -> User:
    """Create or update a User from decoded JWT claims and sync team memberships.

    The user record is keyed on the ``sub`` claim.  On every login the
    email, display_name, role, and last_login fields are refreshed.

    Group memberships from the token are reconciled against the database:
    new teams are created on first encounter (``source="sso"``), memberships
    that are no longer present in the token are removed.

    Args:
        session: Active async DB session (not yet committed).
        claims: Decoded JWT claims dict returned by ``oidc_client.validate_token``.

    Returns:
        Persisted and flushed User instance.
    """
    from app.repositories.team_repo import TeamRepository
    from app.repositories.user_repo import UserRepository

    user_repo = UserRepository(session)
    team_repo = TeamRepository(session)

    sub: str = claims.get("sub", "")
    email: str = claims.get("email", "")
    display_name: str = (
        claims.get("preferred_username") or claims.get("name") or email
    )
    role: str = oidc_client.extract_role(claims)
    groups: list[str] = oidc_client.extract_groups(claims)

    # Upsert user row and refresh last_login
    user = await user_repo.upsert_from_sso(sub, email, display_name, role)

    # ---- Reconcile team memberships ----------------------------------------
    current_team_ids: set[uuid.UUID] = {
        ut.team_id for ut in user.team_memberships
    }

    # Resolve / create a Team row for each group in the token
    sso_teams = []
    for group_name in groups:
        team = await team_repo.get_or_create(group_name, source="sso")
        sso_teams.append(team)

    sso_team_ids: set[uuid.UUID] = {t.id for t in sso_teams}

    # Add memberships that are new in this token
    for team in sso_teams:
        if team.id not in current_team_ids:
            membership = UserTeam(user_id=user.id, team_id=team.id)
            session.add(membership)

    # Remove memberships that are no longer in this token
    for ut in list(user.team_memberships):
        if ut.team_id not in sso_team_ids:
            await session.delete(ut)

    await session.flush()

    # Expire cached relationship so selectinload re-executes
    session.expire(user, ["team_memberships"])
    user = await user_repo.get_by_sub(sub)
    return user


async def _get_or_create_default_user(session: AsyncSession) -> User:
    """Return a stable default admin user for non-SSO deployments.

    The user is keyed by ``sub="default-admin"``.  On first call the row is
    inserted; subsequent calls find and return the existing record.

    Args:
        session: Active async DB session.

    Returns:
        The default admin User instance.
    """
    from app.repositories.user_repo import UserRepository

    user_repo = UserRepository(session)
    user = await user_repo.get_by_sub("default-admin")

    if not user:
        user = User(
            id=uuid.uuid4(),
            sub="default-admin",
            email="admin@local",
            display_name="Admin",
            role="admin",
        )
        session.add(user)
        await session.flush()

    return user
