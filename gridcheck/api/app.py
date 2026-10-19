"""FastAPI application. Run with: uvicorn gridcheck.api.app:create_app --factory"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from gridcheck import config
from gridcheck.api.db import create_pool
from gridcheck.api.routes import router
from gridcheck.domain.grids import GRID_IDS, connection_points

logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT)


def create_app(db_uri: str | None = None) -> FastAPI:
    """Build the app. Tests can pass their own connection string."""

    if db_uri is None:
        db_uri = config.db_uri()
    pool = create_pool(db_uri)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Build the grids now, so the first request doesn't wait for pandapower.
        for grid_id in GRID_IDS:
            connection_points(grid_id)
        await pool.open(wait=True)
        app.state.pool = pool
        try:
            yield
        finally:
            await pool.close()

    app = FastAPI(title="grid-connection-check", lifespan=lifespan)
    app.include_router(router)
    return app
