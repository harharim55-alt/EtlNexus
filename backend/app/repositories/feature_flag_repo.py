"""Feature flag repository — CRUD and access checks for feature flags."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_flag import FeatureFlag
from app.repositories.base import apply_updates


class FeatureFlagRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[FeatureFlag]:
        stmt = select(FeatureFlag).order_by(FeatureFlag.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> FeatureFlag | None:
        stmt = select(FeatureFlag).where(FeatureFlag.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, flag_id: uuid.UUID) -> FeatureFlag | None:
        return await self.session.get(FeatureFlag, flag_id)

    async def update(self, flag_id: uuid.UUID, **kwargs) -> FeatureFlag | None:
        flag = await self.get_by_id(flag_id)
        if not flag:
            return None
        apply_updates(flag, kwargs)
        await self.session.flush()
        return flag

    async def is_enabled_for_user(self, name: str, *, is_beta: bool = False) -> bool:
        flag = await self.get_by_name(name)
        if not flag or not flag.enabled:
            return False
        if flag.beta_only and not is_beta:
            return False
        return True
