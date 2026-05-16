"""Pipeline log service — business logic for multi-log data structure."""

import uuid

from fastapi import HTTPException

from app.repositories.pipeline_log_repo import PipelineLogRepository
from app.schemas.pipeline_log import LogNetworkSchema, LogResponse, LogFieldSchema


class PipelineLogService:
    def __init__(self, log_repo: PipelineLogRepository):
        self.log_repo = log_repo

    async def list_logs(self, pipeline_id: uuid.UUID) -> list[LogResponse]:
        logs = await self.log_repo.list_for_pipeline(pipeline_id)
        return [self._to_response(log) for log in logs]

    async def create_log(self, pipeline_id: uuid.UUID, name: str, ordinal_position: int = 0) -> LogResponse:
        log = await self.log_repo.create(pipeline_id, name, ordinal_position)
        await self.log_repo.session.commit()
        return self._to_response(log)

    async def update_log(self, log_id: uuid.UUID, **kwargs) -> LogResponse:
        log = await self.log_repo.update(log_id, **{k: v for k, v in kwargs.items() if v is not None})
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")
        await self.log_repo.session.commit()
        return self._to_response(log)

    async def delete_log(self, log_id: uuid.UUID):
        deleted = await self.log_repo.delete(log_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Log not found")
        await self.log_repo.session.commit()

    async def set_log_networks(self, log_id: uuid.UUID, networks: list[dict]) -> LogResponse:
        log = await self.log_repo.set_networks(log_id, networks)
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")
        await self.log_repo.session.commit()
        return self._to_response(log)

    async def set_log_fields(self, log_id: uuid.UUID, fields: list[dict]) -> LogResponse:
        log = await self.log_repo.set_fields(log_id, fields)
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")
        await self.log_repo.session.commit()
        return self._to_response(log)

    @staticmethod
    def _to_response(log) -> LogResponse:
        return LogResponse(
            id=log.id,
            pipeline_id=log.pipeline_id,
            name=log.name,
            ordinal_position=log.ordinal_position,
            created_at=log.created_at,
            networks=[
                LogNetworkSchema(
                    id=ln.id,
                    network_id=ln.network_id,
                    network_name=ln.network.name if ln.network else None,
                    retention=ln.retention,
                )
                for ln in (log.networks or [])
            ],
            fields=[
                LogFieldSchema(
                    id=f.id,
                    name=f.name,
                    data_type=f.data_type,
                    ordinal_position=f.ordinal_position,
                )
                for f in (log.fields or [])
            ],
        )
