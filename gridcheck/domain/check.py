"""Check a PV connection request against its grid in the worst case for generation."""

import copy
import time
from collections.abc import Sequence
from typing import Any

import pandapower as pp

from gridcheck import config
from gridcheck.domain.grids import base_network, connection_points
from gridcheck.domain.models import (
    CheckResult,
    Criterion,
    Metrics,
    RequestSpec,
    Verdict,
    Violation,
)


def check(
    grid_id: str, approved: Sequence[RequestSpec], request: RequestSpec
) -> CheckResult:
    """Check ``request`` on top of all requests already ``approved`` on that grid.

    Non-convergence of the load flow is a rejection, not an error. Raises ``KeyError``
    for an unknown grid and ``ValueError`` for a bus that isn't a connection point.
    """
    start = time.perf_counter()
    generation = [*approved, request]
    for spec in generation:
        if spec.bus_id not in connection_points(grid_id):
            raise ValueError(f"bus {spec.bus_id} isn't a connection point of {grid_id}")

    net = copy.deepcopy(base_network(grid_id))
    net.load["scaling"] = config.LOAD_SCALING

    # Reference for the voltage rise: the same case without any generation. Without
    # load and generation this always converges, so a failure here is a real error.
    _run_load_flow(net)
    vm_without_generation = _by_index(net.res_bus.vm_pu)

    for spec in generation:
        pp.create_sgen(
            net,
            spec.bus_id,
            p_mw=spec.p_kw / 1000,
            q_mvar=0.0,
            scaling=config.GENERATION_SCALING,
        )
    try:
        _run_load_flow(net)
    except pp.LoadflowNotConverged:
        return CheckResult(
            verdict=Verdict.REJECTED,
            metrics=Metrics(None, None, None, None),
            violations=(Violation(Criterion.LOAD_FLOW_NOT_CONVERGED),),
            duration_ms=_ms_since(start),
        )

    vm = _by_index(net.res_bus.vm_pu)
    voltage_rise = {bus: vm[bus] - vm_without_generation[bus] for bus in vm}
    line_loading = _by_index(net.res_line.loading_percent)
    trafo_loading = _by_index(net.res_trafo.loading_percent)

    violations = [
        *_exceeding(Criterion.OVERVOLTAGE, config.VM_MAX_PU, vm, "bus"),
        *_exceeding(
            Criterion.VOLTAGE_RISE,
            config.VDE_AR_N_4105_VOLTAGE_RISE_MAX_PU,
            voltage_rise,
            "bus",
        ),
        *_exceeding(
            Criterion.LINE_LOADING, config.LINE_LOADING_MAX_PCT, line_loading, "line"
        ),
        *_exceeding(
            Criterion.TRAFO_LOADING,
            config.TRAFO_LOADING_MAX_PCT,
            trafo_loading,
            "trafo",
        ),
    ]
    return CheckResult(
        verdict=Verdict.REJECTED if violations else Verdict.APPROVED,
        metrics=Metrics(
            vm_max_pu=max(vm.values()),
            voltage_rise_max_pu=max(voltage_rise.values()),
            line_loading_max_pct=max(line_loading.values()),
            trafo_loading_max_pct=max(trafo_loading.values()),
        ),
        violations=tuple(violations),
        duration_ms=_ms_since(start),
    )


def _run_load_flow(net: pp.pandapowerNet) -> None:
    # numba is not installed; disabling it explicitly avoids a warning on every call.
    pp.runpp(net, numba=False)


def _by_index(column: Any) -> dict[int, float]:
    """Turn a pandapower result column (a pandas Series) into element index -> value."""
    return {int(index): float(value) for index, value in column.items()}


def _exceeding(
    criterion: Criterion, limit: float, values: dict[int, float], element_type: str
) -> list[Violation]:
    """One violation per element whose value exceeds the limit."""
    return [
        Violation(criterion, limit, value, f"{element_type} {index}")
        for index, value in values.items()
        if value > limit
    ]


def _ms_since(start: float) -> float:
    return (time.perf_counter() - start) * 1000
