"""UserAuthService — JIT user provisioning and SSO team reconciliation."""

import hashlib
import json
import logging
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.oidc_client import oidc_client
from app.models.user import User
from app.models.user_team import UserTeam
from app.repositories.team_repo import TeamRepository
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

# Short-TTL cache to avoid repeated DB round-trips for the same SSO user
# within a short window.  Keyed by (sub, claims_hash) → (user_id, timestamp).
_PROVISION_CACHE: dict[str, tuple[uuid.UUID, float]] = {}
_CACHE_TTL_SECONDS = 30
_CACHE_MAX_SIZE = 500


def _claims_cache_key(claims: dict) -> str:
    """Derive a cache key from the JWT sub + a hash of role/group claims."""
    sub = claims.get("sub", "")
    # Hash the mutable parts so a role or group change busts the cache
    mutable = json.dumps(
        {
            "email": claims.get("email", ""),
            "roles": claims.get("realm_access", {}).get("roles", []),
            "groups": claims.get("groups", []),
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(mutable.encode()).hexdigest()[:16]
    return f"{sub}:{digest}"


def _evict_stale_entries() -> None:
    """Remove expired entries (and cap size) from the provision cache."""
    now = time.monotonic()
    stale = [k for k, (_, ts) in _PROVISION_CACHE.items() if now - ts > _CACHE_TTL_SECONDS]
    for k in stale:
        del _PROVISION_CACHE[k]
    # Hard cap to prevent unbounded growth
    if len(_PROVISION_CACHE) > _CACHE_MAX_SIZE:
        _PROVISION_CACHE.clear()


class UserAuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._user_repo = UserRepository(session)
        self._team_repo = TeamRepository(session)

    async def upsert_from_claims(self, claims: dict) -> User:
        """Create or update a User from decoded JWT claims and sync team memberships.

        Uses a short-TTL in-memory cache to skip the full provisioning flow
        when the same user hits multiple endpoints within a short window.
        """
        cache_key = _claims_cache_key(claims)
        now = time.monotonic()

        # Check cache — if hit, just load the user by ID (1 query instead of 5+)
        cached = _PROVISION_CACHE.get(cache_key)
        if cached:
            user_id, ts = cached
            if now - ts < _CACHE_TTL_SECONDS:
                user = await self._user_repo.get_by_id(user_id)
                if user:
                    return user
            # Expired or user gone — fall through to full provisioning
            del _PROVISION_CACHE[cache_key]

        user = await self._full_provision(claims)

        # Populate cache
        _evict_stale_entries()
        _PROVISION_CACHE[cache_key] = (user.id, now)

        return user

    async def _full_provision(self, claims: dict) -> User:
        """Full JIT provisioning: upsert user + reconcile team memberships."""
        sub: str = claims.get("sub", "")
        email: str = claims.get("email", "")
        display_name: str = (
            claims.get("preferred_username") or claims.get("name") or email
        )
        role: str = oidc_client.extract_role(claims)
        groups: list[str] = oidc_client.extract_groups(claims)

        # Upsert user row and refresh last_login
        user = await self._user_repo.upsert_from_sso(sub, email, display_name, role)

        # ---- Reconcile team memberships ----------------------------------------
        current_team_ids: set[uuid.UUID] = {
            ut.team_id for ut in user.team_memberships
        }

        # Resolve / create a Team row for each group in the token
        sso_teams = []
        for group_name in groups:
            team = await self._team_repo.get_or_create(group_name, source="sso")
            sso_teams.append(team)

        sso_team_ids: set[uuid.UUID] = {t.id for t in sso_teams}

        # Add memberships that are new in this token
        for team in sso_teams:
            if team.id not in current_team_ids:
                membership = UserTeam(user_id=user.id, team_id=team.id)
                self.session.add(membership)

        # Remove memberships that are no longer in this token
        for ut in list(user.team_memberships):
            if ut.team_id not in sso_team_ids:
                await self.session.delete(ut)

        await self.session.flush()

        # Expire cached relationship so selectinload re-executes
        self.session.expire(user, ["team_memberships"])
        user = await self._user_repo.get_by_sub(sub)
        return user

    async def get_or_create_default_user(self) -> User:
        """Return a stable default admin user for non-SSO deployments.

        The user is keyed by ``sub="default-admin"``.  On first call the row is
        inserted; subsequent calls find and return the existing record.
        Always returns with ``team_memberships`` eagerly loaded.
        """
        user = await self._user_repo.get_by_sub("default-admin")

        if not user:
            user = User(
                id=uuid.uuid4(),
                sub="default-admin",
                email="admin@local",
                display_name="Admin",
                role="admin",
            )
            self.session.add(user)
            await self.session.flush()
            # Reload with selectinload(team_memberships) via the repo
            user = await self._user_repo.get_by_sub("default-admin")

        return user
