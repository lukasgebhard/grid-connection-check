"""FastAPI application. Run with: uvicorn gridcheck.api.app:create_app --factory"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from gridcheck import config
from gridcheck.api.db import Connection, create_pool

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


def create_app(db_uri: str | None = None) -> FastAPI:
    """Build the app. Tests can pass their own connection string."""

    if db_uri is None:
        db_uri = config.db_uri()
    pool = create_pool(db_uri)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await pool.open(wait=True)
        app.state.pool = pool
        try:
            yield
        finally:
            await pool.close()

    app = FastAPI(title="grid-connection-check", lifespan=lifespan)

    @app.get("/livez")
    async def livez() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz(conn: Connection) -> dict[str, str]:
        await conn.execute("SELECT 1")
        return {"status": "ok"}

    return app
