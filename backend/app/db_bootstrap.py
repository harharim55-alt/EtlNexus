"""Ensure the target Postgres database exists before migrations run.

On a fresh/external Postgres server the application database may not exist yet,
so ``alembic upgrade head`` (which creates the tables) can't even connect. This
connects to the maintenance database and issues ``CREATE DATABASE`` when the app
DB is missing. Idempotent and safe to run on every startup: if the DB already
exists it is a no-op, and the tables are then created/updated by Alembic.

Run as a one-shot before Alembic:  ``python -m app.db_bootstrap``
"""

import asyncio
import logging

import asyncpg
from sqlalchemy.engine import make_url

from app.config import settings

logging.basicConfig(level=logging.INFO)
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
        # Don't hard-fail here — let Alembic surface a clear connection error next.
        logger.exception("Could not ensure database %r exists", dbname)
    finally:
        if conn is not None:
            await conn.close()


def main() -> None:
    asyncio.run(ensure_database())


if __name__ == "__main__":
    main()
