"""Inputs and results of a connection check."""

from dataclasses import dataclass
from enum import StrEnum


class Verdict(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class Criterion(StrEnum):
    OVERVOLTAGE = "overvoltage"
    VOLTAGE_RISE = "voltage_rise"
    LINE_LOADING = "line_loading"
    TRAFO_LOADING = "trafo_loading"
    LOAD_FLOW_NOT_CONVERGED = "load_flow_not_converged"


@dataclass(frozen=True)
class RequestSpec:
    """A PV system of ``p_kw`` at the connection point ``bus_id``."""

    bus_id: int
    p_kw: float


@dataclass(frozen=True)
class Violation:
    """One element that exceeds the limit of one criterion.

    For ``LOAD_FLOW_NOT_CONVERGED`` there is no limit, value or element.
    """

    criterion: Criterion
    limit: float | None = None
    value: float | None = None
    element: str | None = None  # e.g. "bus 14", "line 12", "trafo 0"


@dataclass(frozen=True)
class Metrics:
    """Maximum values in the worst case. ``None`` if the load flow did not converge."""

    vm_max_pu: float | None
    voltage_rise_max_pu: float | None
    line_loading_max_pct: float | None
    trafo_loading_max_pct: float | None


@dataclass(frozen=True)
class CheckResult:
    verdict: Verdict
    metrics: Metrics
    violations: tuple[Violation, ...]
    duration_ms: float
