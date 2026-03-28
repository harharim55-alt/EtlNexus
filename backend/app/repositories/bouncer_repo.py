"""Bouncer repository — async SQLAlchemy data access for bouncers."""

import uuid

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bouncer import Bouncer
from app.repositories.base import apply_updates


class BouncerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, skip: int = 0, limit: int = 200) -> list[Bouncer]:
        stmt = (
            select(Bouncer)
            .order_by(Bouncer.display_name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_for_dag_ids(self, dag_ids: set[str]) -> list[Bouncer]:
        """Return bouncers whose dag_ids list overlaps with the given DAG IDs.

        Fetches all bouncers and filters in Python because ``dag_ids`` is
        stored as a JSON column, which does not support native array overlap
        SQL operators without casting.  The bouncer table is expected to remain
        small (O(tens)), making the in-Python filter negligible.

        Args:
            dag_ids: DAG IDs visible to the requesting user.

        Returns:
            Bouncers that participate in at least one of the given DAGs.
        """
        if not dag_ids:
            return []
        all_bouncers = await self.get_all(skip=0, limit=10_000)
        return [b for b in all_bouncers if dag_ids.intersection(b.dag_ids or [])]

    async def get_by_team(self, team: str) -> list[Bouncer]:
        stmt = (
            select(Bouncer)
            .where(Bouncer.team == team)
            .order_by(Bouncer.display_name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name(self, bouncer_name: str) -> Bouncer | None:
        stmt = select(Bouncer).where(Bouncer.bouncer_name == bouncer_name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_names(self, bouncer_names: list[str]) -> list[Bouncer]:
        stmt = (
            select(Bouncer)
            .where(Bouncer.bouncer_name.in_(bouncer_names))
            .order_by(Bouncer.display_name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_teams(self) -> list[str]:
        stmt = (
            select(distinct(Bouncer.team))
            .where(Bouncer.team.is_not(None))
            .order_by(Bouncer.team)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_all_names(self) -> set[str]:
        """Return all bouncer names as a lightweight set (no ORM hydration)."""
        stmt = select(Bouncer.bouncer_name)
        result = await self.session.execute(stmt)
        return {row[0] for row in result.all()}

    async def upsert(self, data: dict) -> Bouncer:
        bouncer_name = data["bouncer_name"]
        existing = await self.get_by_name(bouncer_name)
        if existing:
            apply_updates(existing, data, exclude_keys={"bouncer_name"})
            await self.session.flush()
            return existing
        else:
            bouncer = Bouncer(
                id=uuid.uuid4(),
                bouncer_name=bouncer_name,
                display_name=data.get("display_name", bouncer_name),
                description=data.get("description"),
                team=data.get("team"),
                volume_per_day=data.get("volume_per_day"),
                status=data.get("status"),
                dag_ids=data.get("dag_ids", []),
            )
            self.session.add(bouncer)
            await self.session.flush()
            return bouncer
