"""Tag repository — CRUD for tags and pipeline-tag associations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tag import PipelineTag, Tag


class TagRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self, *, team_id: uuid.UUID | None = None) -> list[Tag]:
        stmt = select(Tag).order_by(Tag.name)
        if team_id is not None:
            stmt = stmt.where(Tag.created_by_team_id == team_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, tag_id: uuid.UUID) -> Tag | None:
        return await self.session.get(Tag, tag_id)

    async def get_by_name(self, name: str) -> Tag | None:
        stmt = select(Tag).where(Tag.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, name: str, created_by_team_id: uuid.UUID | None = None) -> Tag:
        tag = Tag(id=uuid.uuid4(), name=name, created_by_team_id=created_by_team_id)
        self.session.add(tag)
        await self.session.flush()
        return tag

    async def delete(self, tag_id: uuid.UUID) -> bool:
        tag = await self.get_by_id(tag_id)
        if not tag:
            return False
        await self.session.delete(tag)
        await self.session.flush()
        return True

    async def list_for_pipeline(self, pipeline_id: uuid.UUID) -> list[Tag]:
        stmt = (
            select(Tag)
            .join(PipelineTag, PipelineTag.tag_id == Tag.id)
            .where(PipelineTag.pipeline_id == pipeline_id)
            .order_by(Tag.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_pipeline_tags(self, pipeline_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> list[Tag]:
        # Load and delete existing associations individually so the ORM identity map stays consistent
        existing_stmt = select(PipelineTag).where(PipelineTag.pipeline_id == pipeline_id)
        existing = list((await self.session.execute(existing_stmt)).scalars().all())
        for pt in existing:
            await self.session.delete(pt)
        await self.session.flush()

        # Add new associations
        for tag_id in tag_ids:
            self.session.add(PipelineTag(id=uuid.uuid4(), pipeline_id=pipeline_id, tag_id=tag_id))
        await self.session.flush()

        return await self.list_for_pipeline(pipeline_id)
