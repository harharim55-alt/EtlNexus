import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.exceptions import AuthorizationError, PipelineNotFoundError
from app.logging_config import build_log_config
from app.middleware import BodySizeLimitMiddleware, RequestIdMiddleware, RequestLoggingMiddleware
from app.rate_limit import limiter
from app.routers import (
    ai,
    auth,
    data_products,
    health,
    metrics,
    tables,
)

# Structured logging
logging.config.dictConfig(
    build_log_config(
        debug=settings.debug,
        log_format=settings.log_format,
    )
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("ETL Explorer Hub starting up")

    # Refuse to start without SSO in non-development environments
    if settings.deployment_env != "development" and not settings.sso_enabled:
        logger.critical(
            "FATAL: SSO_ENABLED=false in %s environment. Set SSO_ENABLED=true or DEPLOYMENT_ENV=development.",
            settings.deployment_env,
        )
        raise SystemExit(1)
    if not settings.sso_enabled:
        logger.warning("SSO disabled — all requests get admin access (development only)")

    # Ensure the database + the app's own tables exist (idempotent). The external
    # read-only iceberg_table_metrics table is never created here.
    from app.db_bootstrap import bootstrap

    await bootstrap()

    # Initialize OIDC client (no-op if SSO_ENABLED=false)
    from app.integrations.oidc_client import oidc_client

    await oidc_client.initialize()

    yield

    # Shutdown
    from app.integrations.oidc_client import oidc_client as _oidc

    await _oidc.close()
    from app.integrations.llm_client import llm_client

    await llm_client.close()
    from app.integrations.spark_connect_client import spark_connect_client

    spark_connect_client.stop()
    logger.info("ETL Explorer Hub shutting down")


app = FastAPI(
    title="ETL Explorer Hub",
    description="Data architecture command center API",
    version="0.11.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if "*" not in settings.cors_origins else ["*"],
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Accept"],
)

# Pure ASGI middleware (added innermost-first; last = outermost)
app.add_middleware(BodySizeLimitMiddleware, max_size=settings.max_request_body_bytes)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RequestLoggingMiddleware)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status_code": 500},
    )


@app.exception_handler(PipelineNotFoundError)
async def pipeline_not_found_handler(request: Request, exc: PipelineNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, exc: AuthorizationError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


# Routers
app.include_router(health.router, prefix="/api")
app.include_router(data_products.router)
app.include_router(tables.router)
app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(metrics.router)
