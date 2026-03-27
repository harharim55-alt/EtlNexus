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
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.visibility_grant_repo import VisibilityGrantRepository
from app.services.user_auth_service import UserAuthService

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
    """Validate a Bearer JWT and return (or JIT-create) the matching User."""
    auth_service = UserAuthService(session)

    if not settings.sso_enabled:
        return await auth_service.get_or_create_default_user()

    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        claims = await oidc_client.validate_token(credentials.credentials)
    except Exception as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    user = await auth_service.upsert_from_claims(claims)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    return user


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
        auth_service = UserAuthService(session)
        return await auth_service.get_or_create_default_user()

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


async def _resolve_pipeline_team(
    request: Request,
    pipeline_id_param: str,
    session: AsyncSession,
) -> tuple[uuid.UUID | None, object | None]:
    """Parse the pipeline UUID from path params and load the pipeline record.

    Args:
        request: FastAPI Request with path parameters.
        pipeline_id_param: Name of the path parameter holding the pipeline UUID.
        session: Async DB session.

    Returns:
        A 2-tuple of ``(pipeline_uuid, pipeline)``; both ``None`` when the
        parameter is missing or the UUID is invalid.
    """
    raw_pipeline_id: str | None = request.path_params.get(pipeline_id_param)
    if not raw_pipeline_id:
        return None, None
    try:
        pipeline_uuid = uuid.UUID(raw_pipeline_id)
    except ValueError:
        return None, None
    pipeline = await PipelineRepository(session).get_by_id(pipeline_uuid)
    return pipeline_uuid, pipeline


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

        pipeline_uuid, pipeline = await _resolve_pipeline_team(request, pipeline_id_param, session)
        if pipeline_uuid is None:
            return user

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

        pipeline_uuid, pipeline = await _resolve_pipeline_team(request, pipeline_id_param, session)

        # Store loaded pipeline to avoid re-fetching in downstream handler
        request.state.pipeline = pipeline

        if pipeline_uuid is None or not pipeline or not pipeline.team_id:
            return user

        user_team_ids = {ut.team_id for ut in user.team_memberships}

        # Team member — allowed
        if pipeline.team_id in user_team_ids:
            return user

        # Check for editor-level grant
        has_editor = await VisibilityGrantRepository(session).has_editor_grant(
            pipeline_id=pipeline_uuid,
            user_id=user.id,
            user_team_ids=user_team_ids,
            pipeline_team_id=pipeline.team_id,
        )
        if has_editor:
            return user

        raise HTTPException(
            status_code=403,
            detail="Not a member of this pipeline's team and no editor grant",
        )

    return _check


def require_pipeline_visibility(pipeline_id_param: str = "pipeline_id"):
    """Return a dependency that checks the caller can *see* the pipeline.

    Admins bypass the check.  Unassigned pipelines (no team) are visible to
    everyone.  For other pipelines the caller must satisfy the visibility
    grant rules (own team, direct grant, or source-team grant).

    The loaded pipeline is stored on ``request.state.pipeline`` so downstream
    handlers can reuse it without a second DB round-trip.

    Uses HTTP 404 (not 403) when access is denied to prevent pipeline UUID
    enumeration.

    Args:
        pipeline_id_param: Name of the path parameter that carries the
            pipeline UUID (default ``"pipeline_id"``).

    Returns:
        Async dependency function.
    """

    async def _check(
        request: Request,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> User:
        if user.role == "admin":
            return user

        pipeline_uuid, pipeline = await _resolve_pipeline_team(request, pipeline_id_param, session)

        if pipeline_uuid is None:
            return user

        if pipeline is None:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        # Store for downstream reuse
        request.state.pipeline = pipeline

        # Unassigned pipeline — visible to everyone
        if not pipeline.team_id:
            return user

        user_team_ids = {ut.team_id for ut in user.team_memberships}
        can_see = await VisibilityGrantRepository(session).user_can_see_pipeline(
            pipeline_id=pipeline_uuid,
            pipeline_team_id=pipeline.team_id,
            user_id=user.id,
            user_team_ids=user_team_ids,
        )
        if not can_see:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        return user

    return _check


def require_pipeline_visibility_by_name(param_name: str = "etl_name"):
    """Return a dependency that checks pipeline visibility for name-keyed endpoints.

    Looks up the pipeline by ``task_id`` matching the path parameter, then
    performs the same visibility check as ``require_pipeline_visibility``.

    If no pipeline is found for the given name the check is skipped and the
    endpoint is allowed to handle "not found" gracefully.

    Args:
        param_name: Name of the path parameter carrying the ETL task name
            (default ``"etl_name"``).

    Returns:
        Async dependency function.
    """

    async def _check(
        request: Request,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> User:
        if user.role == "admin":
            return user

        etl_name: str | None = request.path_params.get(param_name)
        if not etl_name:
            return user

        pipeline = await PipelineRepository(session).get_by_task_id(etl_name)
        if not pipeline:
            # Let the endpoint handle "not found" gracefully
            return user

        request.state.pipeline = pipeline

        # Unassigned pipeline — visible to everyone
        if not pipeline.team_id:
            return user

        user_team_ids = {ut.team_id for ut in user.team_memberships}
        can_see = await VisibilityGrantRepository(session).user_can_see_pipeline(
            pipeline_id=pipeline.id,
            pipeline_team_id=pipeline.team_id,
            user_id=user.id,
            user_team_ids=user_team_ids,
        )
        if not can_see:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        return user

    return _check
