"""Feature flag schemas — request/response DTOs for feature gating."""

import uuid

from pydantic import BaseModel, ConfigDict


class FeatureFlagResponse(BaseModel):
    id: uuid.UUID
    name: str
    enabled: bool
    beta_only: bool
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FeatureFlagUpdateRequest(BaseModel):
    enabled: bool | None = None
    beta_only: bool | None = None
    description: str | None = None


class FeatureFlagListResponse(BaseModel):
    items: list[FeatureFlagResponse]


class FeatureFlagCheckResponse(BaseModel):
    name: str
    accessible: bool
