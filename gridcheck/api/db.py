from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool


def create_pool(db_uri: str) -> AsyncConnectionPool[AsyncConnection]:
    return AsyncConnectionPool(
        db_uri,
        min_size=1,
        max_size=10,
        open=False,
        kwargs={"autocommit": True},
        check=AsyncConnectionPool.check_connection,
    )


async def get_connection(request: Request) -> AsyncIterator[AsyncConnection]:
    pool: AsyncConnectionPool[AsyncConnection] = request.app.state.pool
    async with pool.connection() as conn:
        yield conn


Connection = Annotated[AsyncConnection, Depends(get_connection)]
