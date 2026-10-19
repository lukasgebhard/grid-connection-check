from gridcheck.domain.grids import GRID_IDS, base_network, connection_points


def test_registry_contains_both_reference_grids() -> None:
    assert sorted(GRID_IDS) == [
        "kerber-landnetz-freileitung-1",
        "kerber-vorstadtnetz-kabel-1",
    ]


def test_base_network_is_built_once_per_process() -> None:
    for grid_id in GRID_IDS:
        assert base_network(grid_id) is base_network(grid_id)


def test_connection_points_are_the_buses_with_a_load() -> None:
    rural = connection_points("kerber-landnetz-freileitung-1")
    suburban = connection_points("kerber-vorstadtnetz-kabel-1")

    assert len(rural) == 13
    assert len(suburban) == 146
    for points in (rural, suburban):
        assert 0 not in points  # medium-voltage side of the transformer
        assert 1 not in points  # low-voltage busbar
