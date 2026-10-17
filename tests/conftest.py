"""Test fixtures backed by a throwaway database.

The test user needs the ``CREATEDB`` privilege.
"""

from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

schema_script = Path(__file__).parents[1] / "db" / "schema.sql"
db_uri = "postgresql://tester:tester@localhost:5432/tester"


@pytest.fixture(scope="session")
async def session_conn() -> AsyncIterator[psycopg.AsyncConnection]:
    """Connect to a fresh database built from the schema, dropped after the run."""

    name = f"test_{uuid4().hex}"

    async with await psycopg.AsyncConnection.connect(db_uri, autocommit=True) as admin:
        await admin.execute(t"CREATE DATABASE {name:i}")
        try:
            async with await psycopg.AsyncConnection.connect(
                make_conninfo(db_uri, dbname=name), autocommit=True
            ) as conn:
                await conn.execute(schema_script.read_bytes())
                yield conn
        finally:
            await admin.execute(t"DROP DATABASE {name:i} WITH (FORCE)")


@pytest.fixture
async def conn(
    session_conn: psycopg.AsyncConnection,
) -> AsyncIterator[psycopg.AsyncConnection]:
    """Yield the test connection inside a transaction that is rolled back afterwards."""

    async with session_conn.transaction(force_rollback=True):
        yield session_conn
