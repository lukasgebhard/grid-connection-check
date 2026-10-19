"""SQL of the API. Rows are returned as ``ConnectionRequest`` models."""

from psycopg import AsyncConnection
from psycopg.rows import class_row

from gridcheck.api.schemas import ConnectionRequest, ConnectionRequestCreate


async def insert_request(
    conn: AsyncConnection, request: ConnectionRequestCreate
) -> ConnectionRequest:
    cur = conn.cursor(row_factory=class_row(ConnectionRequest))
    await cur.execute(
        """
        INSERT INTO connection_requests (grid_id, bus_id, p_kw)
        VALUES (%s, %s, %s)
        RETURNING request_id, grid_id, bus_id, p_kw, status, submitted_at,
                  finished_at, result, error
        """,
        (request.grid_id, request.bus_id, request.p_kw),
    )
    row = await cur.fetchone()
    assert row is not None  # INSERT ... RETURNING always returns the new row
    return row


async def get_request(
    conn: AsyncConnection, request_id: int
) -> ConnectionRequest | None:
    cur = conn.cursor(row_factory=class_row(ConnectionRequest))
    await cur.execute(
        """
        SELECT request_id, grid_id, bus_id, p_kw, status, submitted_at,
               finished_at, result, error
        FROM connection_requests
        WHERE request_id = %s
        """,
        (request_id,),
    )
    return await cur.fetchone()
