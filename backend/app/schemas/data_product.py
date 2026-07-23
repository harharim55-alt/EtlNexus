import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.table import TableRef


class DataProductListItem(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    schedule_type: str | None = None
    team: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DataProductListResponse(BaseModel):
    items: list[DataProductListItem]
    total: int


class DataProductDetail(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    # The catalog tables this product bundles (schema is fetched on demand per table).
    tables: list[TableRef] = []
    documentation: str | None = None
    created_by: str | None = None
    last_updated_by: str | None = None
    last_updated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    team: str | None = None
    can_edit: bool = False
    # Env-templated product-level (read_by_tag) consume snippet.
    default_import_snippet: str = ""
    schedule_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DataProductUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=270)
    documentation: str | None = Field(None, max_length=100_000)
    schedule_type: str | None = Field(None, pattern="^(daily|hourly|stream)$")


class DataProductUpdateResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    documentation: str | None = None
    schedule_type: str | None = None
    last_updated_by: str | None = None
    last_updated_at: datetime | None = None


class ProductRevisionResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    field_name: str
    content: str | None = None
    changed_by: str
    change_source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RevisionListResponse(BaseModel):
    items: list[ProductRevisionResponse]
    total: int
