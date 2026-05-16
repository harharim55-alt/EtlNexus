"""Feature flag service — check and manage feature access."""

import uuid

from fastapi import HTTPException

from app.repositories.feature_flag_repo import FeatureFlagRepository


class FeatureFlagService:
    def __init__(self, flag_repo: FeatureFlagRepository):
        self.flag_repo = flag_repo

    async def list_flags(self):
        return await self.flag_repo.list_all()

    async def check_access(self, flag_name: str, *, is_beta: bool = False) -> bool:
        return await self.flag_repo.is_enabled_for_user(flag_name, is_beta=is_beta)

    async def update_flag(self, flag_id: uuid.UUID, **kwargs):
        result = await self.flag_repo.update(flag_id, **{k: v for k, v in kwargs.items() if v is not None})
        if not result:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        await self.flag_repo.session.commit()
        return result
