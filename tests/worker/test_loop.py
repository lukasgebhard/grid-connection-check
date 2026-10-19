import dataclasses
from collections.abc import Sequence

from gridcheck.domain.check import check
from gridcheck.domain.models import CheckResult, RequestSpec
from tests.worker.helpers import RURAL_GRID, submit, wait_until_decided, worker_thread


def test_worker_decides_a_pending_request(db_uri: str) -> None:
    request_id = submit(db_uri, RURAL_GRID, bus_id=14, p_kw=30)

    with worker_thread(db_uri):
        row = wait_until_decided(db_uri, request_id)

    expected = check(RURAL_GRID, [], RequestSpec(14, 30))
    assert row["status"] == expected.verdict
    assert row["finished_at"] is not None
    assert row["error"] is None
    # Same inputs give the same load flow; only the duration differs.
    assert row["result"]["verdict"] == expected.verdict
    assert row["result"]["metrics"] == dataclasses.asdict(expected.metrics)
    assert row["result"]["violations"] == [
        dataclasses.asdict(violation) for violation in expected.violations
    ]


def failing_check(
    grid_id: str, approved: Sequence[RequestSpec], request: RequestSpec
) -> CheckResult:
    raise RuntimeError("load flow exploded")


def test_failing_check_marks_request_failed_and_worker_keeps_running(
    db_uri: str,
) -> None:
    first = submit(db_uri, RURAL_GRID, bus_id=14, p_kw=30)
    second = submit(db_uri, RURAL_GRID, bus_id=14, p_kw=30)

    with worker_thread(db_uri, check=failing_check) as thread:
        rows = [wait_until_decided(db_uri, first), wait_until_decided(db_uri, second)]
        assert thread.is_alive()

    for row in rows:
        assert row["status"] == "failed"
        assert row["error"] == "RuntimeError: load flow exploded"
        assert row["result"] is None
        assert row["finished_at"] is not None
