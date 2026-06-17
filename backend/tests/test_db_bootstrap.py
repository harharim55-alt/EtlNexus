"""db_bootstrap.ensure_database — mocked asyncpg, no real Postgres."""

from unittest.mock import AsyncMock, patch

from app import db_bootstrap


def _fake_conn(exists):
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=1 if exists else None)
    conn.execute = AsyncMock()
    conn.close = AsyncMock()
    return conn


async def test_creates_database_when_missing():
    conn = _fake_conn(exists=False)
    with patch("app.db_bootstrap.asyncpg.connect", new=AsyncMock(return_value=conn)):
        await db_bootstrap.ensure_database()
    # CREATE DATABASE issued (identifier quoted), connection closed.
    assert conn.execute.await_count == 1
    sql = conn.execute.await_args.args[0]
    assert sql.upper().startswith("CREATE DATABASE")
    conn.close.assert_awaited_once()


async def test_noop_when_database_exists():
    conn = _fake_conn(exists=True)
    with patch("app.db_bootstrap.asyncpg.connect", new=AsyncMock(return_value=conn)):
        await db_bootstrap.ensure_database()
    conn.execute.assert_not_awaited()
    conn.close.assert_awaited_once()
