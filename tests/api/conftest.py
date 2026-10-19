from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection

from gridcheck.api.app import create_app
from gridcheck.api.db import get_connection


@pytest.fixture
async def client(conn: AsyncConnection) -> AsyncIterator[AsyncClient]:
    """Client for the app, with every database call on the rolled-back test connection.

    ASGITransport skips the lifespan, so the app's own pool is never opened.
    """

    async def test_connection() -> AsyncIterator[AsyncConnection]:
        yield conn

    app = create_app("postgresql://unused")
    app.dependency_overrides[get_connection] = test_connection
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
