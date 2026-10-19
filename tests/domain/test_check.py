"""Tests of the pure check function, without a database.

Test inputs keep a clear margin to the limits, so they don't depend on exact values.
"""

import copy

import pytest
from pandapower.toolbox import nets_equal

from gridcheck import config
from gridcheck.domain.check import check
from gridcheck.domain.grids import base_network, connection_points
from gridcheck.domain.models import (
    CheckResult,
    Criterion,
    RequestSpec,
    Verdict,
    Violation,
)

RURAL = "kerber-landnetz-freileitung-1"
SUBURBAN = "kerber-vorstadtnetz-kabel-1"
FAR_END_BUS = 14  # last bus of the rural grid's only feeder


def criteria(result: CheckResult) -> set[Criterion]:
    return {violation.criterion for violation in result.violations}


def test_small_pv_at_far_end_is_approved() -> None:
    result = check(RURAL, [], RequestSpec(FAR_END_BUS, 10.0))

    assert result.verdict == Verdict.APPROVED
    assert result.violations == ()
    assert result.metrics.voltage_rise_max_pu is not None
    assert result.metrics.voltage_rise_max_pu > 0
    assert result.duration_ms > 0


def test_large_pv_at_far_end_is_rejected_for_voltage_rise() -> None:
    result = check(RURAL, [], RequestSpec(FAR_END_BUS, 100.0))

    assert result.verdict == Verdict.REJECTED
    assert criteria(result) == {Criterion.VOLTAGE_RISE}
    assert f"bus {FAR_END_BUS}" in {v.element for v in result.violations}


def test_small_pv_on_suburban_grid_is_approved() -> None:
    bus = max(connection_points(SUBURBAN))

    result = check(SUBURBAN, [], RequestSpec(bus, 10.0))

    assert result.verdict == Verdict.APPROVED


@pytest.mark.parametrize("approved_bus", [FAR_END_BUS, FAR_END_BUS - 1])
def test_approved_requests_count_towards_a_new_request(approved_bus: int) -> None:
    request = RequestSpec(FAR_END_BUS, 25.0)

    alone = check(RURAL, [], request)
    on_top = check(RURAL, [RequestSpec(approved_bus, 25.0)], request)

    assert alone.verdict == Verdict.APPROVED
    assert on_top.verdict == Verdict.REJECTED
    assert criteria(on_top) == {Criterion.VOLTAGE_RISE}


def test_every_violation_is_reported() -> None:
    result = check(RURAL, [], RequestSpec(FAR_END_BUS, 300.0))

    assert result.verdict == Verdict.REJECTED
    assert {Criterion.OVERVOLTAGE, Criterion.VOLTAGE_RISE} <= criteria(result)
    overvoltage = [v for v in result.violations if v.criterion == Criterion.OVERVOLTAGE]
    assert len(overvoltage) > 1  # every affected bus, not just the worst one
    for violation in result.violations:
        assert violation.value is not None
        assert violation.limit is not None
        assert violation.value > violation.limit


def test_non_convergence_is_a_rejection() -> None:
    approved = [RequestSpec(FAR_END_BUS, 1000.0)] * 4

    result = check(RURAL, approved, RequestSpec(FAR_END_BUS, 1000.0))

    assert result.verdict == Verdict.REJECTED
    assert result.violations == (Violation(Criterion.LOAD_FLOW_NOT_CONVERGED),)
    assert result.metrics.vm_max_pu is None


def test_checks_do_not_mutate_the_cached_base_network() -> None:
    before = copy.deepcopy(base_network(RURAL))

    for p_kw in (10.0, 100.0, 300.0, 1000.0):
        approved = [RequestSpec(FAR_END_BUS - 1, p_kw)]
        check(RURAL, approved, RequestSpec(FAR_END_BUS, p_kw))
    check(RURAL, [RequestSpec(FAR_END_BUS, 1000.0)] * 4, RequestSpec(FAR_END_BUS, 1.0))

    assert nets_equal(base_network(RURAL), before)
    assert (base_network(RURAL).load.scaling != config.LOAD_SCALING).all()
    assert base_network(RURAL).sgen.empty


def test_bus_that_is_not_a_connection_point_is_an_error() -> None:
    main_busbar = 1  # carries no load

    with pytest.raises(ValueError, match="connection point"):
        check(RURAL, [], RequestSpec(main_busbar, 10.0))


def test_unknown_grid_is_an_error() -> None:
    with pytest.raises(KeyError):
        check("no-such-grid", [], RequestSpec(FAR_END_BUS, 10.0))
