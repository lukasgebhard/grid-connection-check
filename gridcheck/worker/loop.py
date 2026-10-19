"""The worker loop: claim a job, check it, store the verdict, all in one transaction."""

import logging
import threading
from collections.abc import Callable, Sequence

import psycopg

from gridcheck import config
from gridcheck.domain.check import check as check_request
from gridcheck.domain.models import CheckResult, RequestSpec
from gridcheck.worker import queries

log = logging.getLogger(__name__)

CheckFn = Callable[[str, Sequence[RequestSpec], RequestSpec], CheckResult]


def run_worker(
    db_uri: str,
    stop: threading.Event,
    *,
    check: CheckFn = check_request,
    poll_interval_s: float = config.WORKER_POLL_INTERVAL_S,
    job_timeout_s: int = config.WORKER_JOB_TIMEOUT_S,
) -> None:
    """Process jobs until ``stop`` is set. ``check`` is for tests only.

    Database errors are not caught: the process exits, and since the open job
    transaction is rolled back, its request stays pending for the next worker.
    """
    with psycopg.connect(db_uri, autocommit=True) as conn:
        # The job transaction is idle while the load flow runs. If a worker hangs, the
        # server ends its session after this timeout, which releases the grid lock.
        conn.execute(
            t"SET idle_in_transaction_session_timeout = {job_timeout_s * 1000:l}"
        )
        log.info("worker started")
        while not stop.is_set():
            if not process_next_job(conn, check):
                # process_next_job has already ended its transaction, so the worker
                # holds no transaction (and no locks) while it waits.
                stop.wait(poll_interval_s)
        log.info("worker stopped")


def process_next_job(conn: psycopg.Connection, check: CheckFn) -> bool:
    """Decide the next pending request, if any. Returns whether there was one."""
    with conn.transaction():
        job = queries.claim_next_job(conn)
        if job is None:
            return False

        approved = queries.load_approved(conn, job.grid_id)
        try:
            result = check(job.grid_id, approved, job.request)
        except Exception as exc:
            log.exception("request %d failed", job.request_id)
            queries.store_failure(conn, job.request_id, f"{type(exc).__name__}: {exc}")
        else:
            queries.store_verdict(conn, job.request_id, result)
            log.info(
                "request %d on %s: %s", job.request_id, job.grid_id, result.verdict
            )
    return True
