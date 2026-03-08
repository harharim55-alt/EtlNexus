import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dag_network import DagNetwork


class DagNetworkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_pipeline_id(self, pipeline_id: uuid.UUID) -> list[DagNetwork]:
        stmt = (
            select(DagNetwork)
            .where(DagNetwork.pipeline_id == pipeline_id)
            .order_by(DagNetwork.network_name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def replace_for_pipeline(
        self, pipeline_id: uuid.UUID, network_names: list[str]
    ) -> list[DagNetwork]:
        """Delete existing networks and insert new ones."""
        await self.session.execute(
            delete(DagNetwork).where(DagNetwork.pipeline_id == pipeline_id)
        )
        networks = []
        for name in network_names:
            net = DagNetwork(pipeline_id=pipeline_id, network_name=name)
            self.session.add(net)
            networks.append(net)
        await self.session.flush()
        return networks
