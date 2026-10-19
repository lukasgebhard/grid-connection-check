"""Helpers for worker tests."""

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row

from gridcheck.worker.loop import run_worker

RURAL_GRID = "kerber-landnetz-freileitung-1"


def submit(db_uri: str, grid_id: str, bus_id: int, p_kw: float) -> int:
    """Insert a pending request and return its ID."""
    with psycopg.connect(db_uri, autocommit=True) as conn:
        row = conn.execute(
            "INSERT INTO connection_requests (grid_id, bus_id, p_kw)"
            " VALUES (%s, %s, %s) RETURNING request_id",
            (grid_id, bus_id, p_kw),
        ).fetchone()
    assert row is not None
    request_id: int = row[0]
    return request_id


def wait_until_decided(
    db_uri: str, request_id: int, timeout_s: float = 10.0
) -> dict[str, Any]:
    """Poll until the request is no longer pending and return its row."""
    deadline = time.monotonic() + timeout_s
    with psycopg.connect(db_uri, autocommit=True, row_factory=dict_row) as conn:
        while True:
            row = conn.execute(
                "SELECT * FROM connection_requests WHERE request_id = %s",
                (request_id,),
            ).fetchone()
            assert row is not None
            if row["status"] != "pending":
                return row
            assert time.monotonic() < deadline, f"request {request_id} still pending"
            time.sleep(0.05)


@contextmanager
def worker_thread(db_uri: str, **kwargs: Any) -> Iterator[threading.Thread]:
    """Run ``run_worker`` in a thread and stop it on exit."""
    stop = threading.Event()
    thread = threading.Thread(
        target=run_worker,
        args=(db_uri, stop),
        kwargs={"poll_interval_s": 0.05, **kwargs},
    )
    thread.start()
    try:
        yield thread
    finally:
        stop.set()
        thread.join(timeout=10)
        assert not thread.is_alive()
