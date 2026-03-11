import asyncio
import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import ai, airflow, auth, consumers, dag_summary, health, lineage, pipelines, resources, schema_matrix, sensors, teams, topology, usage, users, visibility
from app.tasks.scheduler import setup_scheduler

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

    # Run initial sync tasks on startup
    from app.tasks.airflow_sync_task import sync_pipelines_from_airflow
    from app.tasks.airflow_poll_task import poll_airflow_statuses
    from app.tasks.catalog_sync_task import sync_from_catalog
    from app.tasks.seed_usage_data import seed_usage_data

    async def _startup_sync():
        try:
            await sync_pipelines_from_airflow()
            await seed_usage_data()
            # Catalog sync runs after pipeline sync to match schemas to existing pipelines
            await sync_from_catalog()
            # Poll only after sync creates pipelines — avoids race on shared tables
            await poll_airflow_statuses()
        except Exception:
            logger.exception("Startup sync failed — app will serve stale/empty data")

    # Run initial syncs in background — don't block app startup
    asyncio.create_task(_startup_sync())

    # Start background scheduler
    sched = setup_scheduler()
    sched.start()
    logger.info("Background scheduler started")

    yield

    # Shutdown
    sched.shutdown(wait=False)
    from app.integrations.airflow_client import airflow_client
    await airflow_client.close()
    from app.integrations.oidc_client import oidc_client as _oidc
    await _oidc.close()
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
app.include_router(sensors.router)
app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(visibility.router)
app.include_router(users.router)
