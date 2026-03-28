import asyncio
import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.exceptions import AirflowSyncError, AuthorizationError, PipelineNotFoundError
from app.logging_config import build_log_config
from app.middleware import BodySizeLimitMiddleware, RequestIdMiddleware, RequestLoggingMiddleware
from app.rate_limit import limiter
from app.routers import (
    ai,
    airflow,
    auth,
    bouncers,
    consumers,
    dag_summary,
    health,
    lineage,
    metrics,
    pipelines,
    resources,
    schema_matrix,
    teams,
    topology,
    usage,
    users,
    visibility,
)

# Structured logging
logging.config.dictConfig(build_log_config(
    debug=settings.debug,
    log_format=settings.log_format,
))

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("ETL Explorer Hub starting up")

    # Refuse to start without SSO in non-development environments
    if settings.deployment_env != "development" and not settings.sso_enabled:
        logger.critical(
            "FATAL: SSO_ENABLED=false in %s environment. "
            "Set SSO_ENABLED=true or DEPLOYMENT_ENV=development.",
            settings.deployment_env,
        )
        raise SystemExit(1)
    if not settings.sso_enabled:
        logger.warning(
            "SSO disabled — all requests get admin access (development only)"
        )

    # Initialize OIDC client (no-op if SSO_ENABLED=false)
    from app.integrations.oidc_client import oidc_client
    await oidc_client.initialize()

    # Initialize Oasis Prod client (no-op if URL not configured)
    from app.integrations.oasis_prod_client import oasis_prod_client
    await oasis_prod_client.initialize()

    # Start Redis cache invalidation bus (no-op if REDIS_URL not set)
    if settings.redis_url:
        from app.cache import invalidation_bus
        try:
            await invalidation_bus.start(settings.redis_url)
        except Exception:
            logger.warning(
                "Failed to connect to Redis at %s — running without "
                "cross-instance cache invalidation",
                settings.redis_url,
                exc_info=True,
            )

    startup_task = None
    sched = None

    if settings.scheduler_enabled:
        from app.tasks.scheduler import run_startup_sync, setup_scheduler

        # Run initial syncs in background — don't block app startup.
        # run_startup_sync waits for Airflow readiness and acquires _sync_lock.
        startup_task = asyncio.create_task(run_startup_sync(), name="startup_sync")

        def _on_startup_done(task: asyncio.Task) -> None:
            if task.cancelled():
                logger.warning("Startup sync was cancelled")
            elif exc := task.exception():
                logger.error("Startup sync failed: %s", exc)
            else:
                logger.info("Startup sync completed successfully")

        startup_task.add_done_callback(_on_startup_done)

        # Start background scheduler (APScheduler 4.x — async)
        sched = await setup_scheduler()
        logger.info("Background scheduler started")
    else:
        logger.info("Scheduler disabled — running in API-only mode")

    yield

    # Shutdown
    if startup_task is not None and not startup_task.done():
        startup_task.cancel()
        logger.info("Cancelled in-progress startup sync")
    if sched is not None:
        await sched.__aexit__(None, None, None)
    from app.integrations.airflow_client import airflow_client
    await airflow_client.close()
    from app.integrations.oidc_client import oidc_client as _oidc
    await _oidc.close()
    from app.integrations.llm_client import llm_client
    await llm_client.close()
    from app.integrations.oasis_prod_client import oasis_prod_client as _oasis
    await _oasis.close()
    from app.integrations.iceberg_client import iceberg_client
    iceberg_client.stop()
    if settings.redis_url:
        from app.cache import invalidation_bus
        await invalidation_bus.stop()
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
app.add_middleware(BodySizeLimitMiddleware, max_size=1_048_576)
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


@app.exception_handler(AirflowSyncError)
async def airflow_sync_error_handler(request: Request, exc: AirflowSyncError):
    return JSONResponse(status_code=502, content={"detail": "Airflow sync error"})


@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, exc: AuthorizationError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


# Routers
app.include_router(health.router, prefix="/api")
app.include_router(pipelines.router)
app.include_router(lineage.router)
app.include_router(airflow.router)
app.include_router(schema_matrix.router)
app.include_router(usage.router)
app.include_router(consumers.router)
app.include_router(topology.router)
app.include_router(resources.router)
app.include_router(dag_summary.router)
app.include_router(bouncers.router)
app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(visibility.router)
app.include_router(users.router)
app.include_router(metrics.router)
