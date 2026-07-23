"""FastAPI authentication and authorisation dependencies.

Identity comes entirely from Keycloak/SSO — nothing about users or teams is
persisted in the database. ``get_current_user`` builds a transient ``AuthUser``
from the JWT claims (username, role, team names). When SSO is disabled (local
dev only) a default admin is returned.

Dependencies provided:
- ``get_current_user`` — requires a valid JWT (or returns the default admin
  when SSO is disabled).
- ``get_current_user_optional`` — returns ``None`` instead of raising.
- ``require_role(*roles)`` — gates a route behind one or more global roles.
- ``require_team_membership(product_id_param)`` — ensures the caller belongs to
  the team that owns the data product being edited.
- ``require_product_visibility(product_id_param)`` — ensures the product exists.
"""

import logging
import uuid
from dataclasses import dataclass, field

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import is_master_admin, settings, team_is_allowed
from app.database import get_db_session
from app.enums import UserRole
from app.integrations.oidc_client import oidc_client
from app.repositories.data_product_repo import DataProductRepository

logger = logging.getLogger(__name__)

# HTTPBearer with auto_error=False so we can return 401 ourselves and also
# support the optional variant without FastAPI raising first.
security = HTTPBearer(auto_error=False)


@dataclass
class AuthUser:
    """A request's authenticated principal, derived from the JWT (not persisted)."""

    username: str
    email: str = ""
    role: str = "member"
    teams: list[str] = field(default_factory=list)
    # Human name (first + last) from the token, for display. Falls back to username.
    full_name: str = ""

    @property
    def display_name(self) -> str:
        # Prefer the human name for display; fall back to the username identifier.
        return self.full_name or self.username

    @property
    def is_master(self) -> bool:
        return is_master_admin(self.username)


# Stable principal used when SSO is disabled (development only).
_DEFAULT_ADMIN = AuthUser(username="admin", email="admin@local", role="admin", teams=[], full_name="Admin")


def _user_from_claims(claims: dict) -> AuthUser:
    """Build a transient AuthUser from decoded JWT claims."""
    username = claims.get("preferred_username") or claims.get("name") or claims.get("email") or claims.get("sub") or ""
    email = claims.get("email", "")
    # SSO roles are ignored — elevated (admin) status comes ONLY from
    # MASTER_ADMIN_USERNAMES. Everyone else is a regular member.
    role = "admin" if is_master_admin(username) else "member"
    # Human name: prefer the "name" claim, else "given_name family_name", else username.
    given = claims.get("given_name") or ""
    family = claims.get("family_name") or ""
    full_name = claims.get("name") or f"{given} {family}".strip() or username
    # Only Keycloak groups permitted by SYSTEM_TEAMS count as teams (["*"] = all).
    # Dedupe case-insensitively (preserving order) so several SSO groups mapped to the
    # same alias collapse into a single team.
    seen: set[str] = set()
    teams: list[str] = []
    for g in oidc_client.extract_groups(claims):
        if team_is_allowed(g) and g.lower() not in seen:
            seen.add(g.lower())
            teams.append(g)
    return AuthUser(username=username, email=email, role=role, teams=teams, full_name=full_name)


# ---------------------------------------------------------------------------
# Core dependency
# ---------------------------------------------------------------------------


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser:
    """Validate a Bearer JWT and return the matching transient AuthUser."""
    if not settings.sso_enabled:
        return _DEFAULT_ADMIN

    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        claims = await oidc_client.validate_token(credentials.credentials)
    except Exception as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    return _user_from_claims(claims)


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser | None:
    """Same as ``get_current_user`` but returns ``None`` instead of raising."""
    if not settings.sso_enabled:
        return _DEFAULT_ADMIN
    if not credentials:
        return None
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Dependency factories
# ---------------------------------------------------------------------------


def require_role(*roles: str):
    """Return a FastAPI dependency that enforces one of the given global roles."""

    async def _check(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions — required one of: {list(roles)}",
            )
        return user

    return _check


async def _resolve_product(
    request: Request,
    product_id_param: str,
    session: AsyncSession,
) -> tuple[uuid.UUID | None, object | None]:
    """Parse the product UUID from path params and load the data product."""
    raw_id: str | None = request.path_params.get(product_id_param)
    if not raw_id:
        return None, None
    try:
        product_uuid = uuid.UUID(raw_id)
    except ValueError:
        return None, None
    product = await DataProductRepository(session).get_by_id(product_uuid)
    return product_uuid, product


def require_team_membership(product_id_param: str = "product_id"):
    """Return a dependency that checks the caller belongs to the product's team.

    Editing is scoped to the owning team for everyone (master admins excepted):
    an admin is a team leader of their own team(s), not a global super-editor.
    Viewers are read-only. Products without an assigned team are editable by any
    non-viewer. Team comparison is case-insensitive.
    """

    async def _check(
        request: Request,
        user: AuthUser = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> AuthUser:
        if user.is_master:
            return user

        if user.role == UserRole.VIEWER:
            raise HTTPException(status_code=403, detail="Viewers cannot edit")

        product_uuid, product = await _resolve_product(request, product_id_param, session)
        if product_uuid is None or not product:
            return user  # missing/unknown product — the endpoint handles 404

        # Unassigned product (no team): only its creator may edit it.
        if not product.team:
            creator = getattr(product, "created_by", None)
            if creator and creator == user.username:
                request.state.product = product
                return user
            raise HTTPException(
                status_code=403,
                detail="Only the creator can edit this unassigned data product",
            )

        if product.team.lower() not in {t.lower() for t in user.teams}:
            raise HTTPException(
                status_code=403,
                detail="Not a member of this product's team",
            )

        request.state.product = product
        return user

    return _check


def require_product_visibility(product_id_param: str = "product_id"):
    """Return a dependency that checks the data product exists.

    Every authenticated user may view any product. The loaded product is stored
    on ``request.state.product`` for downstream reuse. Uses HTTP 404 to avoid
    UUID enumeration.
    """

    async def _check(
        request: Request,
        user: AuthUser = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> AuthUser:
        product_uuid, product = await _resolve_product(request, product_id_param, session)
        if product_uuid is None:
            return user
        if product is None:
            raise HTTPException(status_code=404, detail="Data product not found")
        request.state.product = product
        return user

    return _check
