import asyncio
import logging
import logging.config
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.exceptions import AirflowSyncError, AuthorizationError, PipelineNotFoundError
from app.logging_config import build_log_config, request_id_var
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
from app.routers.metrics import record_request

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

    # Initialize OIDC client (no-op if SSO_ENABLED=false)
    from app.integrations.oidc_client import oidc_client
    await oidc_client.initialize()

    # Initialize Oasis Prod client (no-op if URL not configured)
    from app.integrations.oasis_prod_client import oasis_prod_client
    await oasis_prod_client.initialize()

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

        # Start background scheduler
        sched = setup_scheduler()
        sched.start()
        logger.info("Background scheduler started")
    else:
        logger.info("Scheduler disabled — running in API-only mode")

    yield

    # Shutdown
    if startup_task is not None and not startup_task.done():
        startup_task.cancel()
        logger.info("Cancelled in-progress startup sync")
    if sched is not None:
        sched.shutdown(wait=False)
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
    logger.info("ETL Explorer Hub shutting down")


app = FastAPI(
    title="ETL Explorer Hub",
    description="Data architecture command center API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Accept"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = str(uuid.uuid4())
    request_id_var.set(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# Request logging middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    if request.url.path == "/api/health":
        return await call_next(request)
    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start
    logger.info(
        "%s %s %d %.0fms",
        request.method,
        request.url.path,
        response.status_code,
        duration * 1000,
    )
    record_request(request.method, request.url.path, response.status_code, duration)
    return response


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
