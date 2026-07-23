"""Ensure the application's Postgres database and tables exist.

On a fresh/external Postgres server the application database may not exist yet,
so we connect to the maintenance database and ``CREATE DATABASE`` when missing.
We then create the app's own tables via SQLAlchemy ``create_all``.

The externally-owned, read-only ``iceberg_table_metrics`` table lives on a
separate metadata (see ``app.models.iceberg_metrics``) and is therefore NEVER
created or altered here — the app only reads it.

Both steps are idempotent and safe to run on every startup. Can also be run as a
one-shot:  ``python -m app.db_bootstrap``
"""

import asyncio
import logging

import asyncpg
from sqlalchemy.engine import make_url

from app.config import settings

logger = logging.getLogger("db_bootstrap")


async def ensure_database() -> None:
    """Create the application database if it does not already exist."""
    url = make_url(settings.database_url)
    dbname = url.database
    if not dbname:
        logger.warning("DATABASE_URL has no database name; skipping bootstrap")
        return

    conn = None
    try:
        # Connect to the always-present maintenance DB on the same server.
        conn = await asyncpg.connect(
            host=url.host,
            port=url.port or 5432,
            user=url.username,
            password=url.password,
            database="postgres",
        )
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", dbname)
        if exists:
            logger.info("Database %r already exists — using it", dbname)
            return
        # Identifiers can't be parameterized; dbname comes from trusted config.
        await conn.execute(f'CREATE DATABASE "{dbname}"')
        logger.info("Created database %r", dbname)
    except asyncpg.DuplicateDatabaseError:
        logger.info("Database %r already exists (created concurrently)", dbname)
    except asyncpg.InsufficientPrivilegeError:
        logger.warning(
            "No privilege to CREATE DATABASE %r; assuming it exists or an admin will create it",
            dbname,
        )
    except Exception:
        # Don't hard-fail here — let the table-create step surface a clear error next.
        logger.exception("Could not ensure database %r exists", dbname)
    finally:
        if conn is not None:
            await conn.close()


async def create_tables() -> None:
    """Create the app's own tables if they don't already exist (idempotent).

    Only tables registered on ``Base.metadata`` are created — the external
    ``iceberg_table_metrics`` table is on a separate metadata and untouched.
    """
    from sqlalchemy import text

    import app.models  # noqa: F401  — registers all ORM models on Base.metadata
    from app.database import Base, engine

    async with engine.begin() as conn:
        # Create the app's schema first when it isn't the default public one.
        if settings.db_schema and settings.db_schema != "public":
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.db_schema}"'))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Ensured application tables exist (schema=%s)", settings.db_schema)


async def bootstrap() -> None:
    """Ensure the database exists (optional), then ensure its tables exist."""
    if settings.db_create_database:
        await ensure_database()
    else:
        logger.info("DB_CREATE_DATABASE=false — using the existing database, skipping CREATE DATABASE")
    await create_tables()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(bootstrap())


if __name__ == "__main__":
    main()
