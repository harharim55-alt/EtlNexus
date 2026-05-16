"""Network repository — CRUD for admin-managed networks."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.network import Network
from app.repositories.base import apply_updates


class NetworkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[Network]:
        stmt = select(Network).order_by(Network.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, network_id: uuid.UUID) -> Network | None:
        return await self.session.get(Network, network_id)

    async def get_by_name(self, name: str) -> Network | None:
        stmt = select(Network).where(Network.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, name: str, description: str | None = None) -> Network:
        network = Network(id=uuid.uuid4(), name=name, description=description)
        self.session.add(network)
        await self.session.flush()
        return network

    async def update(self, network_id: uuid.UUID, **kwargs) -> Network | None:
        network = await self.get_by_id(network_id)
        if not network:
            return None
        apply_updates(network, kwargs)
        await self.session.flush()
        return network

    async def delete(self, network_id: uuid.UUID) -> bool:
        network = await self.get_by_id(network_id)
        if not network:
            return False
        await self.session.delete(network)
        await self.session.flush()
        return True
