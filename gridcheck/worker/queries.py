"""SQL of the worker. Every function runs inside the caller's job transaction."""

import dataclasses
from dataclasses import dataclass

from psycopg import Connection
from psycopg.types.json import Jsonb

from gridcheck.domain.models import CheckResult, RequestSpec


@dataclass(frozen=True)
class Job:
    """The pending request a worker checks next."""

    request_id: int
    grid_id: str
    request: RequestSpec


def claim_next_job(conn: Connection) -> Job | None:
    """Lock a grid with pending requests and return its oldest pending request.

    The row lock on the grid is held until the transaction ends, so no other worker
    checks a request of the same grid meanwhile. Grids locked by other workers are
    skipped. Returns ``None`` if no unlocked grid has pending requests.
    """
    row = conn.execute(
        """
        SELECT g.grid_id FROM grids g
        WHERE EXISTS (SELECT 1 FROM connection_requests r
                      WHERE r.grid_id = g.grid_id AND r.status = 'pending')
        ORDER BY g.grid_id
        LIMIT 1
        FOR UPDATE SKIP LOCKED
        """
    ).fetchone()
    if row is None:
        return None
    (grid_id,) = row

    row = conn.execute(
        """
        SELECT request_id, bus_id, p_kw FROM connection_requests
        WHERE grid_id = %s AND status = 'pending'
        ORDER BY request_id
        LIMIT 1
        """,
        (grid_id,),
    ).fetchone()
    # The grid had a pending request, and only the holder of the grid lock decides it.
    assert row is not None
    request_id, bus_id, p_kw = row
    return Job(request_id, grid_id, RequestSpec(bus_id, float(p_kw)))


def load_approved(conn: Connection, grid_id: str) -> list[RequestSpec]:
    rows = conn.execute(
        """
        SELECT bus_id, p_kw FROM connection_requests
        WHERE grid_id = %s AND status = 'approved'
        ORDER BY request_id
        """,
        (grid_id,),
    ).fetchall()
    return [RequestSpec(bus_id, float(p_kw)) for bus_id, p_kw in rows]


def store_verdict(conn: Connection, request_id: int, result: CheckResult) -> None:
    conn.execute(
        """
        UPDATE connection_requests
        SET status = %s, result = %s, finished_at = now()
        WHERE request_id = %s
        """,
        (result.verdict, Jsonb(dataclasses.asdict(result)), request_id),
    )


def store_failure(conn: Connection, request_id: int, error: str) -> None:
    conn.execute(
        """
        UPDATE connection_requests
        SET status = 'failed', error = %s, finished_at = now()
        WHERE request_id = %s
        """,
        (error, request_id),
    )
