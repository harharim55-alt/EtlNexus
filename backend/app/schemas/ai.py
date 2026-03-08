from pydantic import BaseModel


class AIChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AIChatRequest(BaseModel):
    message: str
    history: list[AIChatMessage] = []


class AIChatResponse(BaseModel):
    role: str = "assistant"
    content: str
