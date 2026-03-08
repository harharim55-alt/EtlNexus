from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str
    status_code: int = 500


class HealthCheckResponse(BaseModel):
    status: str
    services: dict[str, str]
