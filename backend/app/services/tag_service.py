"""Tag service — business logic for tag management."""

import uuid

from fastapi import HTTPException

from app.repositories.tag_repo import TagRepository


class TagService:
    def __init__(self, tag_repo: TagRepository):
        self.tag_repo = tag_repo

    async def list_tags(self, *, team_id: uuid.UUID | None = None):
        return await self.tag_repo.list_all(team_id=team_id)

    async def create_tag(self, name: str, created_by_team_id: uuid.UUID | None = None):
        existing = await self.tag_repo.get_by_name(name)
        if existing:
            raise HTTPException(status_code=409, detail=f"Tag '{name}' already exists")
        tag = await self.tag_repo.create(name=name, created_by_team_id=created_by_team_id)
        await self.tag_repo.session.commit()
        return tag

    async def delete_tag(self, tag_id: uuid.UUID):
        deleted = await self.tag_repo.delete(tag_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Tag not found")
        await self.tag_repo.session.commit()

    async def set_pipeline_tags(self, pipeline_id: uuid.UUID, tag_ids: list[uuid.UUID]):
        tags = await self.tag_repo.set_pipeline_tags(pipeline_id, tag_ids)
        await self.tag_repo.session.commit()
        return tags

    async def list_pipeline_tags(self, pipeline_id: uuid.UUID):
        return await self.tag_repo.list_for_pipeline(pipeline_id)
