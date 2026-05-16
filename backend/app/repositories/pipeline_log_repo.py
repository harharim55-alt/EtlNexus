"""Pipeline log repository — CRUD for multi-log data structure."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pipeline_log import PipelineLog, PipelineLogField, PipelineLogNetwork
from app.repositories.base import apply_updates


class PipelineLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_pipeline(self, pipeline_id: uuid.UUID) -> list[PipelineLog]:
        stmt = (
            select(PipelineLog)
            .options(
                selectinload(PipelineLog.networks).selectinload(PipelineLogNetwork.network),
                selectinload(PipelineLog.fields),
            )
            .where(PipelineLog.pipeline_id == pipeline_id)
            .order_by(PipelineLog.ordinal_position)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, log_id: uuid.UUID) -> PipelineLog | None:
        stmt = (
            select(PipelineLog)
            .options(
                selectinload(PipelineLog.networks).selectinload(PipelineLogNetwork.network),
                selectinload(PipelineLog.fields),
            )
            .where(PipelineLog.id == log_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, pipeline_id: uuid.UUID, name: str, ordinal_position: int = 0) -> PipelineLog:
        log = PipelineLog(
            id=uuid.uuid4(),
            pipeline_id=pipeline_id,
            name=name,
            ordinal_position=ordinal_position,
        )
        self.session.add(log)
        await self.session.flush()
        return await self.get_by_id(log.id)

    async def update(self, log_id: uuid.UUID, **kwargs) -> PipelineLog | None:
        log = await self.get_by_id(log_id)
        if not log:
            return None
        apply_updates(log, kwargs)
        await self.session.flush()
        return log

    async def delete(self, log_id: uuid.UUID) -> bool:
        log = await self.session.get(PipelineLog, log_id)
        if not log:
            return False
        await self.session.delete(log)
        await self.session.flush()
        return True

    async def set_networks(
        self, log_id: uuid.UUID, networks: list[dict]
    ) -> PipelineLog | None:
        """Replace all network associations for a log.

        Each dict in networks should have: network_id, retention (optional).
        """
        await self.session.execute(
            delete(PipelineLogNetwork).where(PipelineLogNetwork.log_id == log_id)
        )
        for net in networks:
            self.session.add(
                PipelineLogNetwork(
                    id=uuid.uuid4(),
                    log_id=log_id,
                    network_id=net["network_id"],
                    retention=net.get("retention"),
                )
            )
        await self.session.flush()
        return await self.get_by_id(log_id)

    async def set_fields(
        self, log_id: uuid.UUID, fields: list[dict]
    ) -> PipelineLog | None:
        """Replace all fields for a log."""
        await self.session.execute(
            delete(PipelineLogField).where(PipelineLogField.log_id == log_id)
        )
        for i, field in enumerate(fields):
            self.session.add(
                PipelineLogField(
                    id=uuid.uuid4(),
                    log_id=log_id,
                    name=field["name"],
                    data_type=field.get("data_type"),
                    ordinal_position=field.get("ordinal_position", i),
                )
            )
        await self.session.flush()
        return await self.get_by_id(log_id)
