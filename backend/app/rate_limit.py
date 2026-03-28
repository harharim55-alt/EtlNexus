from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


def get_client_ip(request: Request) -> str:
    if settings.trusted_proxy_depth > 0:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",")]
            idx = -settings.trusted_proxy_depth
            if abs(idx) <= len(parts):
                return parts[idx]
    return get_remote_address(request)


limiter = Limiter(key_func=get_client_ip, default_limits=["200/minute"])
