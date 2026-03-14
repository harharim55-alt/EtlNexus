import asyncio
import logging
import logging.config
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import (
    ai,
    airflow,
    auth,
    bouncers,
    consumers,
    dag_summary,
    health,
    lineage,
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
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "DEBUG" if settings.debug else "INFO",
        "handlers": ["console"],
    },
    "loggers": {
        "uvicorn": {"level": "INFO"},
        "sqlalchemy.engine": {"level": "WARNING"},
        "httpx": {"level": "WARNING"},
        "apscheduler": {"level": "INFO"},
        "py4j": {"level": "ERROR"},
        "pyspark": {"level": "WARNING"},
    },
})

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("ETL Explorer Hub starting up")

    # Initialize OIDC client (no-op if SSO_ENABLED=false)
    from app.integrations.oidc_client import oidc_client
    await oidc_client.initialize()

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

    yield

    # Shutdown
    if not startup_task.done():
        startup_task.cancel()
        logger.info("Cancelled in-progress startup sync")
    sched.shutdown(wait=False)
    from app.integrations.airflow_client import airflow_client
    await airflow_client.close()
    from app.integrations.oidc_client import oidc_client as _oidc
    await _oidc.close()
    from app.integrations.llm_client import llm_client
    await llm_client.close()
    from app.integrations.iceberg_client import iceberg_client
    iceberg_client.stop()
    logger.info("ETL Explorer Hub shutting down")


app = FastAPI(
    title="ETL Explorer Hub",
    description="Data architecture command center API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    if request.url.path == "/api/health":
        return await call_next(request)
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "%s %s %d %.0fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
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
