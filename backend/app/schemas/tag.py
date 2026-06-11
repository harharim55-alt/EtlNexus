"""Tag schemas. A tag is a data product (Pipeline with is_tag), so TagResponse
is just its id + name (populated directly from the tag Pipeline)."""

import uuid

from pydantic import BaseModel, ConfigDict


class TagResponse(BaseModel):
    id: uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class PipelineTagsRequest(BaseModel):
    tag_ids: list[uuid.UUID]


class TagListResponse(BaseModel):
    items: list[TagResponse]
