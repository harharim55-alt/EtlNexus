"""Team repository — async SQLAlchemy data access for teams."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.team import Team
from app.models.user_team import UserTeam


class TeamRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_name(self, name: str) -> Team | None:
        """Find team by name."""
        stmt = select(Team).where(Team.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, team_id: uuid.UUID) -> Team | None:
        """Get team with members eagerly loaded."""
        stmt = (
            select(Team)
            .options(
                selectinload(Team.members).selectinload(UserTeam.user)
            )
            .where(Team.id == team_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, name: str, source: str = "sso") -> Team:
        """Find by name or create. Used by both SSO login and Airflow sync."""
        existing = await self.get_by_name(name)
        if existing:
            return existing

        team = Team(
            id=uuid.uuid4(),
            name=name,
            source=source,
        )
        self.session.add(team)
        await self.session.flush()
        return team

    async def get_all(self, skip: int = 0, limit: int = 200) -> list[Team]:
        """List all teams with member counts."""
        stmt = (
            select(Team)
            .options(selectinload(Team.members))
            .order_by(Team.name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_names(self) -> set[str]:
        """Return set of all team names. Used for task_group prefix matching."""
        stmt = select(Team.name)
        result = await self.session.execute(stmt)
        return {row[0] for row in result.all()}

    async def get_or_create_many(
        self, names: list[str], source: str = "sso"
    ) -> list[Team]:
        """Batch-resolve teams: single SELECT, then create any missing.

        Reduces N serial DB round-trips to 1 SELECT + 1 flush for new teams.
        """
        if not names:
            return []

        stmt = select(Team).where(Team.name.in_(names))
        result = await self.session.execute(stmt)
        existing = {t.name: t for t in result.scalars().all()}

        all_teams = []
        created_any = False
        for name in names:
            if name in existing:
                all_teams.append(existing[name])
            else:
                team = Team(id=uuid.uuid4(), name=name, source=source)
                self.session.add(team)
                all_teams.append(team)
                created_any = True

        if created_any:
            await self.session.flush()
        return all_teams
