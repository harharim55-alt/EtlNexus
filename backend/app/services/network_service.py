"""Network service — business logic for admin-managed network list."""

import uuid

from fastapi import HTTPException

from app.repositories.network_repo import NetworkRepository


class NetworkService:
    def __init__(self, network_repo: NetworkRepository):
        self.network_repo = network_repo

    async def list_networks(self):
        return await self.network_repo.list_all()

    async def create_network(self, name: str, description: str | None = None):
        existing = await self.network_repo.get_by_name(name)
        if existing:
            raise HTTPException(status_code=409, detail=f"Network '{name}' already exists")
        network = await self.network_repo.create(name=name, description=description)
        await self.network_repo.session.commit()
        return network

    async def update_network(self, network_id: uuid.UUID, **kwargs):
        if "name" in kwargs and kwargs["name"] is not None:
            existing = await self.network_repo.get_by_name(kwargs["name"])
            if existing and existing.id != network_id:
                raise HTTPException(status_code=409, detail=f"Network '{kwargs['name']}' already exists")
        result = await self.network_repo.update(network_id, **{k: v for k, v in kwargs.items() if v is not None})
        if not result:
            raise HTTPException(status_code=404, detail="Network not found")
        await self.network_repo.session.commit()
        return result

    async def delete_network(self, network_id: uuid.UUID):
        deleted = await self.network_repo.delete(network_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Network not found")
        await self.network_repo.session.commit()
