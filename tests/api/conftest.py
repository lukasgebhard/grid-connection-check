from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from gridcheck.api.app import create_app


@pytest.fixture
async def client(db_uri: str) -> AsyncIterator[AsyncClient]:
    """Client for the app, connected to the emptied test database.

    ASGITransport doesn't run the lifespan, so the fixture runs it, which opens the
    app's own connection pool just as in production.
    """
    app = create_app(db_uri)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client
