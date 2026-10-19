"""Test fixtures backed by a throwaway database.

The test user needs the ``CREATEDB`` privilege.
"""

from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

schema_script = Path(__file__).parents[1] / "db" / "schema.sql"
admin_db_uri = "postgresql://tester:tester@localhost:5432/tester"


@pytest.fixture(scope="session")
def test_db_uri() -> Iterator[str]:
    """Create a fresh database from the schema, dropped after the run."""

    name = f"test_{uuid4().hex}"

    with psycopg.connect(admin_db_uri, autocommit=True) as admin:
        admin.execute(t"CREATE DATABASE {name:i}")
        try:
            uri = make_conninfo(admin_db_uri, dbname=name)
            with psycopg.connect(uri, autocommit=True) as conn:
                conn.execute(schema_script.read_bytes())
            yield uri
        finally:
            admin.execute(t"DROP DATABASE {name:i} WITH (FORCE)")


@pytest.fixture
def db_uri(test_db_uri: str) -> str:
    """The test database, with no connection requests.

    Tests commit for real: the API and the worker run on their own connections, so
    they only see committed rows, and the worker's job transactions must really commit
    or roll back. Isolation therefore comes from emptying the table before each test,
    not from rolling back after it. The ``grids`` rows are seed data and stay.
    """
    with psycopg.connect(test_db_uri, autocommit=True) as conn:
        conn.execute("TRUNCATE connection_requests")
    return test_db_uri


@pytest.fixture
async def conn(db_uri: str) -> AsyncIterator[psycopg.AsyncConnection]:
    """An autocommit connection to the emptied test database."""
    async with await psycopg.AsyncConnection.connect(db_uri, autocommit=True) as conn:
        yield conn
