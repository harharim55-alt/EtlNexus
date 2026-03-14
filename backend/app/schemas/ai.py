from typing import Literal

from pydantic import BaseModel, Field


class AIChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=10_000)


class AIChatRequest(BaseModel):
    message: str = Field(max_length=5_000)
    history: list[AIChatMessage] = Field(default=[], max_length=50)


class AIChatResponse(BaseModel):
    role: str = "assistant"
    content: str
