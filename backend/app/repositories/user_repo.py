"""User repository — async SQLAlchemy data access for users."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.user_team import UserTeam


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_sub(self, sub: str) -> User | None:
        """Find user by SSO subject identifier."""
        stmt = (
            select(User)
            .options(
                selectinload(User.team_memberships).selectinload(UserTeam.team)
            )
            .where(User.sub == sub)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Find user by ID with team_memberships eagerly loaded."""
        stmt = (
            select(User)
            .options(
                selectinload(User.team_memberships).selectinload(UserTeam.team)
            )
            .where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_from_sso(
        self,
        sub: str,
        email: str,
        display_name: str,
        role: str,
    ) -> User:
        """Create or update user from SSO claims. Updates last_login on every call.

        Uses PostgreSQL ``INSERT ... ON CONFLICT DO UPDATE`` to handle
        concurrent first-login requests atomically.
        """
        now = datetime.now(UTC)
        # If the SSO provider regenerated the user's subject ID (e.g. Keycloak
        # realm re-import), a stale row with the same email but a different sub
        # may exist.  Remove it so the upsert-by-sub can proceed.
        stale = await self.session.execute(
            select(User).where(User.email == email, User.sub != sub)
        )
        stale_user = stale.scalar_one_or_none()
        if stale_user:
            await self.session.delete(stale_user)
            await self.session.flush()

        stmt = (
            pg_insert(User)
            .values(
                id=uuid.uuid4(),
                sub=sub,
                email=email,
                display_name=display_name,
                role=role,
                last_login=now,
            )
            .on_conflict_do_update(
                index_elements=["sub"],
                set_={
                    "email": email,
                    "display_name": display_name,
                    "last_login": now,
                },
            )
            .returning(User.id)
        )
        result = await self.session.execute(stmt)
        user_id = result.scalar_one()
        await self.session.flush()

        # Reload with team memberships eagerly loaded
        loaded = await self.get_by_id(user_id)
        assert loaded is not None
        return loaded

    async def get_all(self, skip: int = 0, limit: int = 200) -> list[User]:
        """List all users with team memberships."""
        stmt = (
            select(User)
            .options(
                selectinload(User.team_memberships).selectinload(UserTeam.team)
            )
            .order_by(User.display_name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        """Count total users."""
        stmt = select(func.count()).select_from(User)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_role(self, user_id: uuid.UUID, role: str) -> User | None:
        """Update user's role (admin only)."""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.role = role
        await self.session.flush()
        return user

    async def update_active(self, user_id: uuid.UUID, is_active: bool) -> User | None:
        """Activate or deactivate a user (admin only)."""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.is_active = is_active
        await self.session.flush()
        return user

    async def count_by_role(self, role: str) -> int:
        """Count users with the given role."""
        stmt = select(func.count()).select_from(User).where(User.role == role)
        result = await self.session.execute(stmt)
        return result.scalar_one()
