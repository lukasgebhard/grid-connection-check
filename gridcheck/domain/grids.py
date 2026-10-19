"""Registry of the grids that requests can be checked against.

The grid IDs must match the rows of the ``grids`` table in ``db/schema.sql``.
"""

from collections.abc import Callable
from functools import cache

import pandapower.networks as pn
from pandapower import pandapowerNet

_CONSTRUCTORS: dict[str, Callable[[], pandapowerNet]] = {
    "kerber-landnetz-freileitung-1": pn.create_kerber_landnetz_freileitung_1,
    "kerber-vorstadtnetz-kabel-1": pn.create_kerber_vorstadtnetz_kabel_1,
}

GRID_IDS: frozenset[str] = frozenset(_CONSTRUCTORS.keys())


@cache
def base_network(grid_id: str) -> pandapowerNet:
    """Build the base network once per process.

    The returned network is shared. Never mutate it; ``copy.deepcopy`` it instead.
    Raises ``KeyError`` for an unknown grid.
    """
    return _CONSTRUCTORS[grid_id]()


@cache
def connection_points(grid_id: str) -> frozenset[int]:
    """The buses that carry an existing load (household connections)."""
    return frozenset(int(bus) for bus in base_network(grid_id).load.bus)
