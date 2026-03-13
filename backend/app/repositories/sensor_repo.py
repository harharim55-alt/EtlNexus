"""Bouncer repository — async SQLAlchemy data access for bouncers."""

import uuid

from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor import Bouncer


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

    async def get_by_team(self, team: str) -> list[Bouncer]:
        stmt = (
            select(Bouncer)
            .where(Bouncer.team == team)
            .order_by(Bouncer.display_name)
        )
        stmt = self._apply_date_filter(stmt, date_from, date_to)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name(self, sensor_name: str) -> Bouncer | None:
        stmt = select(Bouncer).where(Bouncer.sensor_name == sensor_name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_names(self, sensor_names: list[str]) -> list[Bouncer]:
        stmt = (
            select(Bouncer)
            .where(Bouncer.sensor_name.in_(sensor_names))
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

    async def upsert(self, data: dict) -> Bouncer:
        sensor_name = data["sensor_name"]
        existing = await self.get_by_name(sensor_name)
        if existing:
            for key, value in data.items():
                if key != "sensor_name" and hasattr(existing, key):
                    setattr(existing, key, value)
            await self.session.flush()
            return existing
        else:
            bouncer = Bouncer(
                id=uuid.uuid4(),
                sensor_name=sensor_name,
                display_name=data.get("display_name", sensor_name),
                description=data.get("description"),
                team=data.get("team"),
                volume_per_day=data.get("volume_per_day"),
                status=data.get("status"),
                dag_ids=data.get("dag_ids", []),
            )
            self.session.add(bouncer)
            await self.session.flush()
            return bouncer
