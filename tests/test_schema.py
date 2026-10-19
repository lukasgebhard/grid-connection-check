import psycopg
import pytest
from psycopg import AsyncConnection, sql

grid_id = "kerber-landnetz-freileitung-1"


async def test_new_request_is_pending(conn: AsyncConnection) -> None:
    cur = await conn.execute(
        "INSERT INTO connection_requests (grid_id, bus_id, p_kw) VALUES (%s, 14, 30)"
        " RETURNING status, submitted_at, finished_at, result, error",
        (grid_id,),
    )
    status, submitted_at, finished_at, result, error = await cur.fetchone() or ()
    assert status == "pending"
    assert submitted_at is not None
    assert (finished_at, result, error) == (None, None, None)


@pytest.mark.parametrize(
    "assignments",
    [
        "p_kw = 0",
        "p_kw = 1000.01",
        "finished_at = now()",  # still pending
        "status = 'approved', finished_at = now()",  # no result
        "status = 'approved', result = '{}'",  # no finished_at
        "status = 'failed', finished_at = now()",  # no error
        "status = 'failed', finished_at = now(), error = 'boom', result = '{}'",
    ],
)
async def test_inconsistent_requests_are_rejected(
    conn: AsyncConnection, assignments: str
) -> None:
    await conn.execute(
        "INSERT INTO connection_requests (grid_id, bus_id, p_kw) VALUES (%s, 14, 30)",
        (grid_id,),
    )
    update = sql.SQL("UPDATE connection_requests SET {}").format(sql.SQL(assignments))

    with pytest.raises(psycopg.errors.CheckViolation):
        await conn.execute(update)


async def test_request_for_unknown_grid_is_rejected(conn: AsyncConnection) -> None:
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        await conn.execute(
            "INSERT INTO connection_requests (grid_id, bus_id, p_kw)"
            " VALUES ('no-such-grid', 14, 30)"
        )
