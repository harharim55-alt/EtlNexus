from datetime import datetime

from pydantic import BaseModel


class DagNetworkSchema(BaseModel):
    network_name: str
    last_synced_at: datetime | None = None

    model_config = {"from_attributes": True}


class DagNetworksResponse(BaseModel):
    pipeline_id: str
    networks: list[DagNetworkSchema]
